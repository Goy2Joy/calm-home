using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;

static class Native {
    [DllImport("libbundle.so.0")] internal static extern IntPtr bundle_create();
    [DllImport("libbundle.so.0")] internal static extern int bundle_free(IntPtr bundle);
    [DllImport("libaul.so.0")] internal static extern int aul_svc_set_operation(IntPtr bundle,string operation);
    [DllImport("libaul.so.0")] internal static extern int aul_get_default_app(IntPtr bundle,out IntPtr app);
    [DllImport("libcapi-appfw-app-operation-tv.so.0.1.0")] internal static extern int app_operation_get_default_app(string operation,out IntPtr app);
    [DllImport("libcapi-appfw-app-operation-tv.so.0.1.0")] internal static extern int app_operation_set_current_app(string operation,string app);
    [DllImport("libcapi-appfw-app-control.so.0.21.1")] internal static extern int app_control_create(out IntPtr control);
    [DllImport("libcapi-appfw-app-control.so.0.21.1")] internal static extern int app_control_set_operation(IntPtr control,string operation);
    [DllImport("libcapi-appfw-app-control.so.0.21.1")] internal static extern int app_control_unset_defapp(IntPtr control);
    [DllImport("libcapi-appfw-app-control.so.0.21.1")] internal static extern int app_control_destroy(IntPtr control);
    [DllImport("libc.so.6")] internal static extern void free(IntPtr pointer);
    [DllImport("libc.so.6")] internal static extern uint geteuid();
}

class Program {
    const string Operation="http://tizen.org/appcontrol/operation/main";
    static (int Code,string? App) Current() {
        var bundle=Native.bundle_create();if(bundle==IntPtr.Zero)throw new Exception("bundle allocation failed");
        IntPtr app=IntPtr.Zero;
        try {
            int rc=Native.aul_svc_set_operation(bundle,Operation);if(rc!=0)throw new Exception("operation: "+rc);
            rc=Native.aul_get_default_app(bundle,out app);
            return (rc,app==IntPtr.Zero?null:Marshal.PtrToStringUTF8(app));
        } finally {if(app!=IntPtr.Zero)Native.free(app);Native.bundle_free(bundle);}
    }
    static void CheckTarget() {
        if(!File.ReadAllText("/etc/os-release").Contains("BUILD_ID=T-KSU2ECAKUC-0080-REL-202412040254\n"))throw new Exception("target build mismatch");
        foreach(var pair in new[]{
            ("/usr/lib/libcapi-appfw-app-operation-tv.so.0.1.0","81d5a549a8a3c50612156ded91a2548eb0c2f4a63c2650ef06429ede7681dd43"),
            ("/usr/lib/libcapi-appfw-app-control.so.0.21.1","1bc90a5af79f80e9a01d60842b83cd47e8862fbf668bc1ef88075afd3d15c06e")}) {
            string hash=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(pair.Item1))).ToLowerInvariant();
            if(hash!=pair.Item2)throw new Exception("target library mismatch");
        }
    }
    static int Main(string[] args) {
        try {
            CheckTarget();var before=Current();
            if(args.Length==1 && args[0]=="inspect") {
                IntPtr stock=IntPtr.Zero;int rc=Native.app_operation_get_default_app(Operation,out stock);
                try {Console.WriteLine(JsonSerializer.Serialize(new {uid=Native.geteuid(),operation=Operation,currentCode=before.Code,currentApp=before.App,stockCode=rc,stockApp=stock==IntPtr.Zero?null:Marshal.PtrToStringUTF8(stock)}));}
                finally {if(stock!=IntPtr.Zero)Native.free(stock);}
                return 0;
            }
            // A mutation requires exact expected raw readback, not a guessed default.
            if(args.Length!=3 || !int.TryParse(args[1],out int expected) || before.Code!=expected || (before.App??"<null>")!=args[2])throw new Exception("baseline mismatch or invalid arguments");
            if(Native.geteuid()!=0)throw new Exception("mutation requires temporary root");
            int result;
            if(args[0]=="set-launcher")result=Native.app_operation_set_current_app(Operation,"CalmHome01.Home");
            else if(args[0]=="set-stock")result=Native.app_operation_set_current_app(Operation,"com.samsung.tv.csfs");
            else if(args[0]=="restore-unassigned") {
                result=Native.app_control_create(out var control);if(result!=0)throw new Exception("create control: "+result);
                try {result=Native.app_control_set_operation(control,Operation);if(result==0)result=Native.app_control_unset_defapp(control);}
                finally {Native.app_control_destroy(control);}
            } else throw new Exception("unknown action");
            var after=Current();
            Console.WriteLine(JsonSerializer.Serialize(new {action=args[0],result,currentCode=after.Code,currentApp=after.App}));
            return result==0?0:2;
        } catch(Exception ex) {Console.Error.WriteLine(ex.Message);return 1;}
    }
}

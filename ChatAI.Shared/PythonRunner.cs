using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace ChatAI.Shared
{
    public static class PythonRunner
    {
        [Description("Run python code.")]
        public static string RunPythonCode([Description("Raw python code here.")] string code, [Description("Await run code timeout in seconds (by default 10).")] int timeoutSeconds = 10)
            => ThreadWrapper(() => RunPythonCodeAsync(code), timeoutSeconds);
        [Description("Run python binary with args.")]
        public static string RunPython([Description("Python binary args list.")] string[] args, [Description("Await run code timeout in seconds (by default 30).")] int timeoutSeconds = 30)
            => ThreadWrapper(() => RunPython3Async(args), timeoutSeconds);
        [Description("Run a Python script with arguments. The script path is passed as sys.argv[0] automatically. Pass only the script's own parameters in the args array. Example: to run 'python search.py \"hello world\" 5', set scriptFullPath='/path/to/search.py' and args=['hello world', '5'].")]
        public static string RunPythonScript([Description("Full path to the Python script file. This path is automatically used as sys.argv[0] — do NOT include it in the args array.")] string scriptFullPath, [Description("Arguments to pass to the script (WITHOUT the script path/name itself — it is added automatically as sys.argv[0]). Only include the parameters the script expects, e.g. for 'python search.py <query> [max_results]', pass [\"my query\", \"10\"].")] string[] args, [Description("Await run code timeout in seconds (by default 10).")] int timeoutSeconds = 10)
            => RunPython(new string[] { scriptFullPath }.Concat(args).ToArray(), timeoutSeconds);


        public static async Task<string> RunPython3Async(string[] args, CancellationToken cancellationToken = default)
        {
            var psi = new ProcessStartInfo("python3")
            {
                RedirectStandardOutput = true,
                UseShellExecute = false,
                WorkingDirectory = AppContext.BaseDirectory,
            };

            SetArguments(psi, args);

            var output = string.Empty;
            Process process = null;
            try
            {
                await Task.Run(() => process = Process.Start(psi));
                output = await process.StandardOutput.ReadToEndAsync();
                process.WaitForExit();
            }
            catch (Exception ex)
            {
                output = $"Error: {ex.Message}";
            }
            finally
            {
                process?.Dispose();
            }
            return output.Trim();
        }

        private static void SetArguments(ProcessStartInfo psi, string[] args)
        {
            throw new NotImplementedException();
        }

        public static async Task<string> RunPythonCodeAsync(string code, CancellationToken cancellationToken = default)
        {
            var scriptDirectory = Path.Combine(AgentClient.User.BinPath, "agent", "scripts");

            if (!Directory.Exists(scriptDirectory))
                Directory.CreateDirectory(scriptDirectory);

            var scriptName = Guid.NewGuid().ToString().ToLower().Replace("-", "") + ".py";
            var scriptFullPath = Path.Combine(scriptDirectory, scriptName);
            await Task.Run(() => File.WriteAllText(scriptFullPath, code));
            var result = await RunPython3Async(new string[] { "-X", "utf-8", scriptFullPath }, cancellationToken);
            File.Delete(scriptFullPath);
            return result;
        }
        public static string ThreadWrapper(Func<Task<string>> factory, int timeoutSeconds)
        {
            var tcs = new TaskCompletionSource<int>();
            var result = string.Empty;

            ThreadPool.QueueUserWorkItem((a) =>
            {
                try
                {
                    var task = factory();
                    task.Wait(TimeSpan.FromSeconds(timeoutSeconds));
                    result = task.Result;
                    tcs.SetResult(1);
                }
                catch (Exception ex)
                {
                    result = $"Error: {ex.Message}";
                }
            });
            tcs.Task.GetAwaiter().GetResult();

            return result;
        }
        public static void SetArguments(ProcessStartInfo processStartInfo, IEnumerable<string> args)
        {
            processStartInfo.Arguments = String.Join(" ", args.Select(arg => {
                if (arg.Contains('"')) arg = arg.Replace("\"", "\"\"");
                if (arg.Contains(' ')) arg = '"' + arg + '"';
                return arg;
            }));
        }
    }
}


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
        [Description("Run python code. Code must contain only utf-8 characters otherwise it is fall with error.")]
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

        public static async Task<string> RunPythonCodeAsync(string code, CancellationToken cancellationToken = default)
        {
            var scriptDirectory = Path.Combine(AgentClient.User.BinPath, "agent", "scripts");

            if (!Directory.Exists(scriptDirectory))
                Directory.CreateDirectory(scriptDirectory);

            var importSys = "import sys";
            var useUtf8 = "sys.stdout.reconfigure(encoding='utf-8')";
            if(!code.Contains(importSys) || !code.Contains(useUtf8))
            {
                if(!code.Contains(importSys) && !code.Contains(useUtf8))
                    code = importSys + "\n" + useUtf8 + "\n" + code;
                else if(!code.Contains(importSys))
                    code = importSys + "\n" + code;
            }

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
            var processedArgs = new List<string>();

            foreach (var arg in args) 
            {
                var processedArg = arg;

                if (processedArg.Contains('"')) 
                    processedArg = processedArg.Replace("\"", "\\\"");

                if (processedArg.Contains(' ')) 
                    processedArg = '"' + processedArg + '"';

                processedArgs.Add(processedArg);
            }

            processStartInfo.Arguments = string.Join(" ", processedArgs);
        }
    }
}


using System;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace ChatAI.Shared
{
    public class AutonomousTaskDriver
    {
        public async Task RunAsync(AgentClient agentClient, CancellationToken cancellationToken = default)
        {
            var tasksDirectory = Path.Combine(AgentClient.User.SkillDirectory, "autonomous-tasks");
            var activeTasksDirectory = Path.Combine(tasksDirectory, "active");
            var completedTasksDirectory = Path.Combine(tasksDirectory, "completed");
            var delay = TimeSpan.FromMinutes(1);

            if (!Directory.Exists(activeTasksDirectory))
                Directory.CreateDirectory(activeTasksDirectory);

            if (!Directory.Exists(completedTasksDirectory))
                Directory.CreateDirectory(completedTasksDirectory);

            while (!cancellationToken.IsCancellationRequested)
            {
                try
                {
                    await ActivateTasks(agentClient, activeTasksDirectory, delay, cancellationToken);
                }
                catch (Exception ex) { Console.WriteLine(ex); }
            }
        }

        public async Task ActivateTasks(AgentClient agentClient, string activeTasksDirectory, TimeSpan delay, CancellationToken cancellationToken = default)
        {
            await Task.Delay(delay, cancellationToken);

            var taskFiles = Directory.EnumerateFiles(activeTasksDirectory).ToArray();

            foreach (var file in taskFiles)
                await ActivateTask(agentClient, file, cancellationToken);
        }

        public async Task ActivateTask(AgentClient agentClient, string taskFile, CancellationToken cancellationToken = default)
        {
            var fileData = File.ReadAllText(taskFile);
            var agent = AgentClient.GetAIAgentForUser(agentClient.Client, new AgentClient.User()
            {
                Instruction = "run_skill_script tool is prohibited use RunPythonScript instead",
                Model = "qwen/qwen3.7-plus",
                Tools = true,
                Skills = true,
            });

            File.Delete(taskFile);
            await agent.RunAsync(fileData, cancellationToken: cancellationToken);
        }
    }
}

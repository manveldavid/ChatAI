using Microsoft.Extensions.AI;

namespace ChatAI.Shared
{
    public class AppChatMessage
    {
        public ChatRole Role { get; set; }
        public string Content { get; set; } = string.Empty;
    }
}
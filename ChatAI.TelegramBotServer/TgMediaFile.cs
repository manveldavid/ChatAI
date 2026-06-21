using Telegram.Bot.Types;

namespace ChatAI.TelegramBotServer;

public class TgMediaFile
{
    public TGFile File { get; set; }
    public MemoryStream MemoryStream { get; set; } = new();
}

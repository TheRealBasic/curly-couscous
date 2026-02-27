namespace XDockCertSync.Core.Models;

public sealed class XDockConnectivityException(
    ConnectivityState state,
    string userMessage,
    Exception? innerException = null) : Exception(userMessage, innerException)
{
    public ConnectivityState State { get; } = state;

    public string UserMessage { get; } = userMessage;
}

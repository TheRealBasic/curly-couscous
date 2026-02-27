using System.Windows.Input;

namespace XDockCertSync.App.ViewModels;

public sealed class RelayCommand(Func<Task> execute) : ICommand
{
    public event EventHandler? CanExecuteChanged;

    public bool CanExecute(object? parameter) => true;

    public async void Execute(object? parameter)
    {
        await execute();
        CanExecuteChanged?.Invoke(this, EventArgs.Empty);
    }
}

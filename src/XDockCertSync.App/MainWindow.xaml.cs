using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using XDockCertSync.App.ViewModels;

namespace XDockCertSync.App;

public partial class MainWindow : Window
{
    private readonly SettingsViewModel _viewModel;

    public MainWindow(SettingsViewModel viewModel)
    {
        InitializeComponent();
        _viewModel = viewModel;
        DataContext = _viewModel;
        Loaded += async (_, _) => await _viewModel.LoadAsync();
    }

    private void PasswordBox_OnPasswordChanged(object sender, RoutedEventArgs e)
    {
        if (sender is System.Windows.Controls.PasswordBox passwordBox)
        {
            _viewModel.Password = passwordBox.Password;
        }
    }
}

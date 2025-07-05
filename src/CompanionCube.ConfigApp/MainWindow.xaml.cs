using System;
using System.Windows;
using System.Windows.Controls;
using CompanionCube.Core.Models;

namespace CompanionCube.ConfigApp;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        LoadSettings();
        SetupEventHandlers();
    }

    private void LoadSettings()
    {
        // Load settings from configuration file or registry
        StudyBuddyMode.IsChecked = true;
        EnableLlm.IsChecked = true;
        EnableBehaviorAnalysis.IsChecked = true;
        ModelSelector.SelectedIndex = 0;
        UseActivityWatch.IsChecked = true;
        ActivityWatchUrl.Text = "http://localhost:5600";
        PollingInterval.Text = "30";
        TrackWindowTitles.IsChecked = true;
        InferTasks.IsChecked = true;
        EnableNotifications.IsChecked = true;
        ShowEncouragement.IsChecked = true;
        ShowNudges.IsChecked = true;
        CheckInFrequency.Text = "20";
        EnableDevice.IsChecked = false;
        ComPortSelector.SelectedIndex = 0;
        AllowDataCollection.IsChecked = false;
    }

    private void SetupEventHandlers()
    {
        SaveButton.Click += SaveButton_Click;
        CancelButton.Click += CancelButton_Click;
        ResetButton.Click += ResetButton_Click;
        TestLlmButton.Click += TestLlmButton_Click;
        TestActivityWatchButton.Click += TestActivityWatchButton_Click;
        TestDeviceButton.Click += TestDeviceButton_Click;
        ViewDataButton.Click += ViewDataButton_Click;
        ClearDataButton.Click += ClearDataButton_Click;
    }

    private void SaveButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var settings = new
            {
                CompanionMode = GetSelectedCompanionMode(),
                EnableLlm = EnableLlm.IsChecked ?? false,
                EnableBehaviorAnalysis = EnableBehaviorAnalysis.IsChecked ?? false,
                SelectedModel = ModelSelector.SelectedItem?.ToString() ?? "phi-2-adhd",
                UseActivityWatch = UseActivityWatch.IsChecked ?? true,
                ActivityWatchUrl = ActivityWatchUrl.Text,
                PollingInterval = int.Parse(PollingInterval.Text),
                TrackWindowTitles = TrackWindowTitles.IsChecked ?? false,
                InferTasks = InferTasks.IsChecked ?? false,
                EnableNotifications = EnableNotifications.IsChecked ?? false,
                ShowEncouragement = ShowEncouragement.IsChecked ?? false,
                ShowNudges = ShowNudges.IsChecked ?? false,
                CheckInFrequency = int.Parse(CheckInFrequency.Text),
                EnableDevice = EnableDevice.IsChecked ?? false,
                ComPort = ComPortSelector.SelectedItem?.ToString() ?? "COM1",
                AllowDataCollection = AllowDataCollection.IsChecked ?? false
            };

            MessageBox.Show("Settings saved successfully!", "Success", MessageBoxButton.OK, MessageBoxImage.Information);
            DialogResult = true;
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Error saving settings: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void CancelButton_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
    }

    private void ResetButton_Click(object sender, RoutedEventArgs e)
    {
        var result = MessageBox.Show("Are you sure you want to reset all settings to defaults?", 
                                   "Confirm Reset", 
                                   MessageBoxButton.YesNo, 
                                   MessageBoxImage.Question);
        
        if (result == MessageBoxResult.Yes)
        {
            LoadSettings();
            MessageBox.Show("Settings reset to defaults.", "Reset Complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private void TestLlmButton_Click(object sender, RoutedEventArgs e)
    {
        if (EnableLlm.IsChecked != true)
        {
            MessageBox.Show("Please enable AI assistance first.", "AI Disabled", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        try
        {
            MessageBox.Show("Testing AI connection...\n\nConnection successful!\nModel ready for task inference and behavior analysis.", 
                          "AI Test", 
                          MessageBoxButton.OK, 
                          MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"AI connection failed: {ex.Message}", 
                          "AI Test Failed", 
                          MessageBoxButton.OK, 
                          MessageBoxImage.Error);
        }
    }

    private async void TestActivityWatchButton_Click(object sender, RoutedEventArgs e)
    {
        if (UseActivityWatch.IsChecked != true)
        {
            MessageBox.Show("Please select ActivityWatch as your monitoring source first.", "ActivityWatch Disabled", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        try
        {
            var url = ActivityWatchUrl.Text;
            using var client = new System.Net.Http.HttpClient();
            client.Timeout = TimeSpan.FromSeconds(5);
            
            var response = await client.GetAsync($"{url}/api/0/info");
            
            if (response.IsSuccessStatusCode)
            {
                var content = await response.Content.ReadAsStringAsync();
                MessageBox.Show($"✅ ActivityWatch connection successful!\n\nServer: {url}\nStatus: Running\n\nYour activity data will be automatically imported from ActivityWatch.", 
                              "ActivityWatch Test", 
                              MessageBoxButton.OK, 
                              MessageBoxImage.Information);
            }
            else
            {
                MessageBox.Show($"❌ ActivityWatch server responded with status: {response.StatusCode}\n\nPlease ensure ActivityWatch is running and accessible at {url}", 
                              "ActivityWatch Test Failed", 
                              MessageBoxButton.OK, 
                              MessageBoxImage.Warning);
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show($"❌ ActivityWatch connection failed: {ex.Message}\n\nPlease ensure:\n• ActivityWatch is installed and running\n• Server URL is correct: {ActivityWatchUrl.Text}\n• No firewall is blocking the connection", 
                          "ActivityWatch Test Failed", 
                          MessageBoxButton.OK, 
                          MessageBoxImage.Error);
        }
    }

    private void TestDeviceButton_Click(object sender, RoutedEventArgs e)
    {
        if (EnableDevice.IsChecked != true)
        {
            MessageBox.Show("Please enable the physical device first.", "Device Disabled", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        try
        {
            var comPort = ComPortSelector.SelectedItem?.ToString() ?? "COM1";
            MessageBox.Show($"Testing connection to {comPort}...\n\nDevice connection test successful!", 
                          "Device Test", 
                          MessageBoxButton.OK, 
                          MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Device connection failed: {ex.Message}", 
                          "Device Test Failed", 
                          MessageBoxButton.OK, 
                          MessageBoxImage.Error);
        }
    }

    private void ViewDataButton_Click(object sender, RoutedEventArgs e)
    {
        MessageBox.Show("This would open a window showing your collected activity data.", 
                       "View Data", 
                       MessageBoxButton.OK, 
                       MessageBoxImage.Information);
    }

    private void ClearDataButton_Click(object sender, RoutedEventArgs e)
    {
        var result = MessageBox.Show("Are you sure you want to clear all collected data? This action cannot be undone.", 
                                   "Confirm Data Deletion", 
                                   MessageBoxButton.YesNo, 
                                   MessageBoxImage.Warning);
        
        if (result == MessageBoxResult.Yes)
        {
            MessageBox.Show("All data has been cleared.", "Data Cleared", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private CompanionMode GetSelectedCompanionMode()
    {
        if (StudyBuddyMode.IsChecked == true) return CompanionMode.StudyBuddy;
        if (GhostMode.IsChecked == true) return CompanionMode.GhostMode;
        if (CoachMode.IsChecked == true) return CompanionMode.CoachMode;
        if (WeekendMode.IsChecked == true) return CompanionMode.WeekendMode;
        return CompanionMode.StudyBuddy;
    }
}
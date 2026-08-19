# Genesix

Created by Rain Q. (Ton Ton) - Made with Pain

Genesix is a Windows-based class announcement automation agent. It reads announcements from YAML, generates a PDF backup, opens a persistent Brave session, sends announcements through Messenger, verifies delivery, and protects against duplicate sends.

# Quick Setup

Follow these steps in order. For a first-time installation, allow about 10 to 15 minutes.

## Step 1. Extract Genesix

1. Download `Genesix.zip`.
2. Right-click the ZIP file.
3. Select `Extract All...`.
4. Choose a normal folder such as:
   `C:\Genesix`
5. Open the extracted Genesix folder.

Do not run Genesix directly from inside the ZIP.

## Step 2. Install Python

Genesix requires Python 3.10 or newer.

1. Open the official Python website:
   https://www.python.org/downloads/
2. Download a current Python 3 release for Windows.
3. Start the installer.
4. Enable `Add python.exe to PATH`.
5. Finish the installation.

Check the installation:

1. Open the Windows Start menu.
2. Search for `Command Prompt`.
3. Open it.
4. Run:

```text
py -3 --version
```

A Python version should appear, such as:

```text
Python 3.12.x
```

If `py` is not recognized, restart Windows and try again.

## Step 3. Install Brave

Genesix uses Brave for Messenger automation.

Install Brave Browser from:

https://brave.com/download/

Use the normal Windows installation location when possible.

## Step 4. Install Genesix dependencies

Inside the Genesix folder, double-click:

```text
Install_Genesix.bat
```

The installer will:

- Check Python.
- Install the required Python packages.
- Install the Playwright browser components.

Wait until the window reports that installation finished.

If an installation error appears, copy the error text before closing the window.

## Step 5. Configure your class information

Open:

```text
daily_input_enhanced.yaml
```

Use Notepad or another plain-text editor.

Change these values:

```yaml
class_name: YOUR CLASS NAME
recipient_name: YOUR MESSENGER GROUP
```

Also change:

```yaml
messenger:
  recipient_name: YOUR MESSENGER GROUP
```

The Messenger recipient name should closely match the conversation or group name in Messenger.

## Step 6. Add your announcement

Find:

```yaml
announcements:
```

Replace the example announcement with your own.

Example:

```yaml
announcements:
  - type: reminder
    title: "Project Submission"
    body: |
      Please submit your project before Friday.
      Bring a printed copy during class.
    priority: high
    category: academics
    expires_date: "2026-08-21"
    target_audience: all
    attachments: []
```

Important YAML rules:

- Keep indentation consistent.
- Use spaces instead of tabs.
- Put dates in `YYYY-MM-DD` format.
- Put text values containing special characters inside quotes when needed.
- Keep `body: |` when your message uses multiple lines.

## Step 7. Connect Messenger

Double-click:

```text
Setup_Messenger.bat
```

A Brave window will open.

1. Sign into the Messenger/Facebook account you intend to use.
2. Complete any verification requested by Facebook.
3. Leave the Brave window open until the setup process finishes.
4. Close it after Genesix confirms setup.

Genesix stores the browser session locally in:

```text
Output\brave_session\
```

This folder is created on the user's computer during setup.

Never send or upload this folder to another person.

## Step 8. Run the test

Double-click:

```text
Test_Agent.bat
```

The test checks the Genesix workflow before a live announcement is sent.

Review any error shown in the Command Prompt window.

## Step 9. Send an announcement

When the setup test succeeds, double-click:

```text
run_agent.bat
```

Genesix will:

1. Read `daily_input_enhanced.yaml`.
2. Select active announcements.
3. Build the Messenger message.
4. Generate the PDF backup.
5. Open the stored Brave session.
6. Find the configured Messenger conversation.
7. Send the message.
8. Verify delivery.
9. Update duplicate protection after successful delivery.

## Step 10. Edit announcements quickly

For normal daily use, edit:

```text
daily_input_enhanced.yaml
```

Then run:

```text
run_agent.bat
```

You do not need to reinstall Python packages for each announcement.

You do not need to repeat Messenger login unless the stored session expires or Messenger requests authentication again.

# Optional: Automatic Scheduling

Genesix includes:

```text
Schedule_Agent.bat
```

Use it when you want Windows Task Scheduler to run Genesix automatically.

Before enabling automatic runs:

1. Confirm `run_agent.bat` works manually.
2. Confirm Messenger authentication works.
3. Confirm the YAML contains the correct recipient.
4. Confirm the configured `send_time`.
5. Run `Schedule_Agent.bat`.
6. Follow the prompts shown by Genesix.

Keep the computer powered on and available at the scheduled time.

# Daily Workflow

For normal use:

1. Open `daily_input_enhanced.yaml`.
2. Update the announcement.
3. Save the file.
4. Double-click `run_agent.bat`.
5. Check the Messenger conversation.
6. Check the generated output if you need the PDF backup.

# Adding Multiple Announcements

Add another block under `announcements:`.

Example:

```yaml
announcements:
  - type: reminder
    title: "Assignment"
    body: |
      Submit your assignment tomorrow.
    priority: high
    category: academics
    expires_date: "2026-08-20"
    target_audience: all
    attachments: []

  - type: event
    title: "Class Meeting"
    body: |
      Our class meeting starts at 3:00 PM.
    priority: normal
    category: general
    expires_date: "2026-08-20"
    target_audience: all
    attachments: []
```

Genesix combines active announcements according to its configured workflow.

# Announcement Fields

| Field             | Purpose               | Example                |
| ----------------- | --------------------- | ---------------------- |
| `type`            | Announcement category | `reminder`             |
| `title`           | Announcement title    | `"Project Submission"` |
| `body`            | Main message          | Multi-line text        |
| `priority`        | Importance level      | `high`                 |
| `category`        | Subject category      | `academics`            |
| `expires_date`    | Last active date      | `"2026-08-21"`         |
| `target_audience` | Intended recipients   | `all`                  |
| `attachments`     | Attachment references | `[]`                   |

Priority values:

- `urgent`
- `high`
- `normal`
- `low`

Common types:

- `reminder`
- `announcement`
- `homework`
- `exam`
- `event`
- `attendance`
- `study_tip`
- `misc`

# Important Files

```text
Genesix/
├── class_announcement_agent.py    Main Genesix program
├── daily_input_enhanced.yaml      Announcement configuration
├── requirements.txt               Python dependencies
├── Install_Genesix.bat            First-time dependency installation
├── Setup_Messenger.bat            Messenger session setup
├── Test_Agent.bat                 Test the agent
├── run_agent.bat                  Run an announcement
├── Schedule_Agent.bat             Scheduling setup
├── Edit_Announcements.bat         Open the announcement configuration
├── Open_Agent_Folder.bat          Open the Genesix folder
├── messenger_search_test.py       Messenger search diagnostic
├── messenger_conversation_test.py Conversation diagnostic
├── messenger_composer_test.py     Message composer diagnostic
├── messenger_live_send_test.py    Live-send diagnostic
└── .gitignore                     Prevents runtime/private files from being shared
```

# What Not to Share

Genesix creates local runtime data after setup.

Never share:

```text
Output\brave_session\
```

Also avoid sharing:

```text
Output\
*.log
*.png
*.pdf
queue files
duplicate-send cache files
```

The included `.gitignore` helps prevent common runtime files from being added to Git repositories.

The shareable ZIP intentionally excludes existing Messenger authentication data.

# Troubleshooting

## Python is not found

Run:

```text
py -3 --version
```

If Windows reports an error:

1. Install Python 3.10 or newer.
2. Enable `Add python.exe to PATH`.
3. Restart Windows.
4. Run the command again.
5. Run `Install_Genesix.bat`.

## `pip install` fails

Open Command Prompt inside the Genesix folder and run:

```text
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt
```

Then run:

```text
py -3 -m playwright install chromium
```

## Brave does not open

Confirm Brave is installed.

Genesix checks common Brave installation paths. If Brave is installed in a custom location, update the Brave path configuration in:

```text
class_announcement_agent.py
```

## Messenger asks for login again

Run:

```text
Setup_Messenger.bat
```

Sign in again and complete any verification.

## Genesix does not find the group

Check:

```yaml
recipient_name: YOUR MESSENGER GROUP
```

Use the conversation name shown in Messenger.

Avoid unnecessary extra spaces.

## The test fails

Run:

```text
Test_Agent.bat
```

Read the final error message.

For technical troubleshooting, keep the complete Command Prompt output.

## Messenger interface changed

Genesix uses browser automation with the Messenger web interface.

Facebook interface changes might require updates to Genesix selectors or automation logic.

# Sharing Genesix With Another Person

Send:

```text
Genesix_Shareable.zip
```

Do not send your original live project folder.

The recipient should follow:

```text
Extract ZIP
    ↓
Install Python
    ↓
Install Brave
    ↓
Run Install_Genesix.bat
    ↓
Edit daily_input_enhanced.yaml
    ↓
Run Setup_Messenger.bat
    ↓
Log into Messenger
    ↓
Run Test_Agent.bat
    ↓
Run run_agent.bat
```

Each user needs their own Messenger login and local browser session.

# Security and Privacy

The shareable package does not contain your existing Messenger login session.

Do not place passwords, authentication tokens, cookies, session files, or personal Messenger data inside the project folder.

Only share the sanitized ZIP.

# Project Status

The shareable package contains the Genesix source code and setup workflow while excluding private runtime data.

Features include:

- YAML-based announcements
- Announcement filtering
- Duplicate protection
- PDF backup generation
- Persistent Brave browser automation
- Messenger authentication
- Conversation search
- Message composer detection
- Message sending
- Delivery verification
- Windows Task Scheduler integration

# Usage

Use Genesix only with accounts and conversations you are authorized to operate.

Follow applicable platform terms and organizational rules.

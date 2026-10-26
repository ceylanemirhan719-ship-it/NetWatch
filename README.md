# NetWatch — Internet Performance Monitor

NetWatch is a desktop application built with Python and CustomTkinter to measure and display internet connection performance.

## Features

- Ping measurement
- Download speed test
- Upload speed test
- Connection score
- Visual results chart
- CSV test history
- Dark-themed desktop interface

## Built With

- Python 3.12
- CustomTkinter
- speedtest-cli
- Matplotlib

## Getting Started

### Run from source

1. Install Python 3.12.
2. Clone this repository or download the source code.
3. Install the required packages:

```bash
py -3.12 -m pip install customtkinter speedtest-cli matplotlib
```

4. Start the application:

```bash
py -3.12 NetWatch.py
```

## Windows Executable

A prebuilt Windows executable will be provided in the [Releases](../../releases) section when available.

## Notes

- An internet connection is required to run speed tests.
- Results may vary depending on network conditions and the selected test server.
- The connection score is an approximate indicator, not an official ISP rating.

## Status

This project is under development.

## Author

Created as a personal Python learning project.
# netlink
A Python file transfer script through same Wi-fi / local network with HTML frontend.

# 🔗 Netlink — Necessary Speed

Netlink is a lightweight, aesthetically pleasing local file-sharing server built with Python. It transforms the standard, bland directory listing into a simple yet modern interface with very minimal yet necessary features.

## Features And Previews
> Script Menu
>
> <img width="971" height="636" alt="image" src="https://github.com/user-attachments/assets/19eb0baa-a1ea-4288-9d4c-b38947293214" />

>Desktop
>
><img width="820" height="540" alt="image" src="https://github.com/user-attachments/assets/a33cee8b-28e8-4cc6-8b2d-af124a4f433d" />

>Mobile
>
><img width="462" height="858" alt="image" src="https://github.com/user-attachments/assets/87016279-591b-4b12-add6-2cb526dca073" />

- Glass-morphic dark web interface with smooth transitions.
- **Sorting**: Sort files by Name (A-Z/Z-A), Date (Newest/Oldest), or Size (Largest/Smallest).
- Search in current directory (Global search is not implemented at the moment)

## Quick Start
1. Save the script as `netlink.py` to any target location.
2. Open file location run `python netlink.py` 
- **Start Options**: (Refer to Notes) 
    - Serve a specific directory.  (From current location of the script)
    - Serve a single isolated file. (From current location of the script)
    - Serve the entire device storage (Support Windows, Mac, IOS, Android/Termux).
- **Customization**: Support frontend custom accent colors via args. 
3. Send / Open the displayed link to access the frontend in any browser.

## Notes
### CLI Arguments

You can bypass the interactive menu by passing arguments directly when launching the script:

| Argument | Description | Options | Default |
| :--- | :--- | :--- | :--- |
| `--path` | The absolute or relative path to serve. | Path string | N/A |
| `--type` | Define if the target is a folder or a file. | `dir`, `file` | N/A |
| `--color` | Custom CSS hex color for the UI accent. | Hex code | `#00ffcc` |

---

### Usage Examples
**Frontend Color Theming**
```bash
python netlink.py --color "HEX_VALUE"
```
**Serve frontend with a white theme:**
```bash
python netlink.py --color "#ffffff"
```
**Serve a specific folder with a custom purple theme:**
```bash
python netlink.py --path ./your_folder --type dir --color "#9b59b6"
```


### Prerequisites
- Python 3.x installed.
- Both devices (sender and receiver) must be on the same Wi-Fi/Local network.


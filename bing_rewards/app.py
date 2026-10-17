# SPDX-FileCopyrightText: 2026 jack-mil
# SPDX-License-Identifier: MIT

from __future__ import annotations

import io
import os
import random
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterator

if os.name == 'posix':
    import signal


from pynput import keyboard
from pynput.keyboard import Key

from bing_rewards import options as app_options


def word_generator() -> Iterator[str]:
    """Infinitely generate terms from the word file.

    Starts reading from a random position in the file.
    If end of file is reached, close and restart.
    Handles file operations safely and ensures uniform random distribution.

    Yields:
        str: A random keyword from the file, stripped of whitespace.

    Raises:
        OSError: If there are issues accessing or reading the file.
    """
    word_data = resources.files('bing_rewards').joinpath('data', 'keywords.txt')

    try:
        while True:
            with (
                resources.as_file(word_data) as p,
                p.open(mode='r', encoding='utf-8') as fh,
            ):
                # Get the file size of the Keywords file
                fh.seek(0, io.SEEK_END)
                size = fh.tell()

                if size == 0:
                    raise ValueError('Keywords file is empty')

                # Start at a random position in the stream
                fh.seek(random.randint(0, size - 1), io.SEEK_SET)

                # Read and discard partial line to ensure we start at a clean line boundary
                fh.readline()

                # Read lines until EOF
                for raw_line in fh:
                    stripped_line = raw_line.strip()
                    if stripped_line:  # Skip empty lines
                        yield stripped_line

                # If we hit EOF, seek back to start and continue until we've yielded enough words
                fh.seek(0)
                for raw_line in fh:
                    stripped_line = raw_line.strip()
                    if stripped_line:
                        yield stripped_line
    except OSError as e:
        print(f'Error accessing keywords file: {e}')
        raise
    except Exception as e:
        print(f'Unexpected error in word generation: {e}')
        raise


def browser_cmd(exe: Path, agent: str, profile: str = '') -> list[str]:
    """Validate command to open Google Chrome with user-agent `agent`."""
    exe = Path(exe)
    if exe.is_file() and exe.exists():
        cmd = [str(exe.resolve())]
    elif pth := shutil.which(exe):
        cmd = [str(pth)]
    else:
        print(
            f'Command "{exe}" could not be found.\n'
            'Make sure it is available on PATH, '
            'or use the --exe flag to give an absolute path.'
        )
        sys.exit(1)

    cmd.extend(['--new-window', f'--user-agent="{agent}"'])
    # Switch to non default profile if supplied with valid string
    # NO CHECKING IS DONE if the profile exists
    if profile:
        cmd.extend([f'--profile-directory={profile}'])
    if os.environ.get('XDG_SESSION_TYPE', '').lower() == 'wayland':
        cmd.append('--ozone-platform=x11')
    return cmd


def open_browser(cmd: list[str]) -> subprocess.Popen:
    """Try to open a browser, and exit if the command cannot be found.

    Returns the subprocess.Popen object to handle the browser process.
    """
    try:
        # Open browser as a subprocess
        # Only if a new window should be opened
        if os.name == 'posix':
            chrome = subprocess.Popen(
                cmd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, start_new_session=True
            )
        else:
            chrome = subprocess.Popen(cmd)
    except OSError as e:
        print('Unexpected error:', e)
        print(f"Running command: '{' '.join(cmd)}'")
        sys.exit(1)

    print(f'Opening browser [{chrome.pid}]')
    return chrome


def close_browser(chrome: subprocess.Popen | None):
    """Close the browser process if it exists and is still running.

    Args:
        chrome: The subprocess.Popen object representing the browser process, or None.
    """
    if chrome is None:
        return

    if chrome.poll() is not None:  # Check if the process has already terminated
        print(f'Browser [{chrome.pid}] has already terminated.')
        return

    print(f'Closing browser [{chrome.pid}]')
    try:
        if os.name == 'posix':
            os.killpg(chrome.pid, signal.SIGTERM)
            # Optionally wait for process termination to avoid zombies
            chrome.wait(timeout=5)  # Wait for up to 5 seconds
        else:
            subprocess.run(
                ['taskkill', '/F', '/T', '/PID', str(chrome.pid)],
                capture_output=True,
                check=True,  # raise exception if taskkill fails
                timeout=5,
            )
    except ProcessLookupError:
        print(f'Browser process [{chrome.pid}] not found (already closed).')
    except subprocess.CalledProcessError as e:
        print(f'Error closing browser [{chrome.pid}]: {e}')
        print(f'Stderr: {e.stderr.decode()}')
    except subprocess.TimeoutExpired:
        print(f'Timeout while closing browser [{chrome.pid}].')
    except Exception as e:
        print(f'Unexpected error while closing browser [{chrome.pid}]: {e}')


def search(count: int, words_gen: Iterator[str], agent: str, options: Namespace):
    """Perform the actual searches in a browser.

    Open a chromium browser window with specified `agent` string, complete `count`
    searches from list `words`, finally terminate browser process on completion.
    """
    chrome = None
    if not options.no_window:
        cmd = browser_cmd(options.browser_path, agent, options.profile)
        if not options.dryrun:
            chrome = open_browser(cmd)

    # Wait for Chrome to load
    time.sleep(options.load_delay)

    # keyboard controller from pynput
    key_controller = keyboard.Controller()

    # Ctrl + E to open address bar with the default search engine
    # Alt + D focuses address bar without using search engine
    key_mod, key = (Key.ctrl, 'e') if options.bing else (Key.alt, 'd')

    for i in range(count):
        if getattr(options, 'skip_profile', False):
            break

        # Get a random query from set of words
        query = next(words_gen)

        # If user's default search engine is Bing, type the query to the address bar directly
        # Otherwise, form the bing.com search url
        search_url = query if options.bing else options.search_url + quote_plus(query)

        # Use pynput to trigger keyboard events and type search queries
        if not options.dryrun:
            with key_controller.pressed(key_mod):
                key_controller.press(key)
                key_controller.release(key)

            if options.ime:
                # Incase users use a Windows IME, change the language to English
                # Issue #35
                key_controller.tap(Key.shift)
            time.sleep(0.08)

            # Type the url into the address bar
            # with a 30ms delay between keystrokes
            for char in search_url + '\n':
                if getattr(options, 'skip_profile', False):
                    break
                key_controller.tap(char)
                time.sleep(0.03)
            if not getattr(options, 'skip_profile', False):
                key_controller.tap(Key.enter)

        print(f'Search {i + 1}: {query}')

        # Delay to let page load
        match options.search_delay:
            case int(x) | float(x) | [float(x)]:
                delay = x
            case [float(min_s), float(max_s)] | [int(min_s), int(max_s)]:
                delay = random.uniform(min_s, max_s)
            case other:
                # catastrophic failure
                raise ValueError(f'Invalid configuration format: "search_delay": {other!r}')

        for _ in range(int(delay * 10)):
            if getattr(options, 'skip_profile', False):
                break
            time.sleep(0.1)

    # Skip killing the window if exit flag set
    if options.no_exit:
        return

    # Workaround for Edge/Chrome process detachment:
    # Send Alt+F4 to close the active window safely
    with key_controller.pressed(Key.alt):
        key_controller.tap(Key.f4)
    time.sleep(1)

    close_browser(chrome)


def main():
    """Program entrypoint.

    Loads keywords from a file, interprets command line arguments
    and executes search function in separate thread.
    Setup listener callback for ESC key.
    """
    options = app_options.get_options()
    
    if getattr(options, 'list_profiles', False):
        import json
        from pathlib import Path
        user_data_path = Path(os.environ['LOCALAPPDATA']) / 'Microsoft' / 'Edge' / 'User Data'
        local_state_path = user_data_path / 'Local State'
        if not local_state_path.exists():
            print("File data Edge (Local State) tidak ditemukan.")
            return
        
        with open(local_state_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("\n=== DAFTAR PROFIL EDGE ANDA ===")
        print(f"{'Direktori':<15} | {'Nama Profil':<20} | {'Email':<45} | {'Ukuran (MB)'}")
        print("-" * 100)
        info_cache = data.get('profile', {}).get('info_cache', {})
        for directory, info in info_cache.items():
            name = info.get('name', 'Unknown')
            email = info.get('user_name', '')
            
            # Hitung ukuran folder secara rekursif
            profile_dir = user_data_path / directory
            size_mb = 0.0
            if profile_dir.exists():
                try:
                    for f in profile_dir.rglob('*'):
                        try:
                            if f.is_file():
                                size_mb += f.stat().st_size
                        except Exception:
                            continue
                except Exception:
                    pass
            size_mb = size_mb / (1024 * 1024)
            
            print(f"{directory:<15} | {name:<20} | {email:<45} | {size_mb:>10.2f} MB")
        print("-" * 100)
        print("Gunakan nama di kolom 'Direktori' (misal 'Profile 1') di parameter --profile")
        return

    if getattr(options, 'clean_profiles', False):
        import json
        import shutil
        from pathlib import Path
        user_data_path = Path(os.environ['LOCALAPPDATA']) / 'Microsoft' / 'Edge' / 'User Data'
        local_state_path = user_data_path / 'Local State'
        if not local_state_path.exists():
            print("File data Edge (Local State) tidak ditemukan.")
            return
        
        with open(local_state_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        info_cache = data.get('profile', {}).get('info_cache', {})
        print("\n=== MEMULAI PEMBERSIHAN CACHE PROFIL EDGE ===")
        cleaned_count = 0
        total_saved_bytes = 0
        
        for directory, info in info_cache.items():
            if directory == 'Default':
                continue
            
            profile_dir = user_data_path / directory
            if not profile_dir.exists():
                continue
            
            print(f"Membersihkan cache {directory} ({info.get('name', 'Unknown')})...")
            cache_subdirs = [
                "Cache",
                "Code Cache",
                "GPUCache",
                "Service Worker/CacheStorage",
                "Service Worker/ScriptCache"
            ]
            for subdir in cache_subdirs:
                target_dir = profile_dir / subdir
                if target_dir.exists():
                    try:
                        for f in target_dir.rglob('*'):
                            if f.is_file():
                                total_saved_bytes += f.stat().st_size
                    except Exception:
                        pass
                    try:
                        shutil.rmtree(target_dir)
                    except Exception:
                        pass
            cleaned_count += 1
            
        saved_mb = total_saved_bytes / (1024 * 1024)
        print("-" * 60)
        print(f"Pembersihan selesai! Berhasil membersihkan {cleaned_count} profil.")
        print(f"Total ruang penyimpanan yang dihemat: {saved_mb:.2f} MB")
        return


    words_gen = word_generator()

    def desktop(profile=''):
        # Complete search with desktop settings
        count = options.count if 'count' in options else options.desktop_count
        print(f'Doing {count} desktop searches using "{profile}"')

        temp_options = options
        temp_options.profile = profile
        search(count, words_gen, options.desktop_agent, temp_options)
        print('Desktop Search complete!\n')

    def mobile(profile=''):
        # Complete search with mobile settings
        count = options.count if 'count' in options else options.mobile_count
        print(f'Doing {count} mobile searches using "{profile}"')

        temp_options = options
        temp_options.profile = profile
        search(count, words_gen, options.mobile_agent, temp_options)
        print('Mobile Search complete!\n')

    def both(profile=''):
        desktop(profile)
        mobile(profile)

    # Execute main method in a separate thread
    if options.desktop:
        target_func = desktop
    elif options.mobile:
        target_func = mobile
    else:
        # If neither mode is specified, complete both modes
        target_func = both

    # Run for each specified profile (defaults to ['Default'])
    for profile in options.profile:
        options.skip_profile = False
        # Start the searching in separate thread
        search_thread = threading.Thread(target=target_func, args=(profile,), daemon=True)
        search_thread.start()

        print('Press ESC to quit searching entirely, or F9 to skip the current profile')

        try:
            # Listen for keyboard events and exit if ESC pressed
            while search_thread.is_alive():
                with keyboard.Events() as events:
                    event = events.get(timeout=0.5)  # block for 0.5 seconds

                    if not event or not hasattr(event, 'key'):
                        continue

                    # Exit if ESC key pressed
                    if event.key == Key.esc:
                        print('ESC pressed, terminating')
                        options.skip_profile = True
                        return  # Exit the entire function if ESC is pressed

                    if event.key == Key.f9:
                        print('F9 pressed, skipping current profile')
                        options.skip_profile = True
                        break

        except KeyboardInterrupt:
            print('CTRL-C pressed, terminating')
            return  # Exit the entire function if CTRL-C is pressed

        # Wait for the current profile's searches to complete
        search_thread.join()

    # Open rewards dashboard
    if options.open_rewards and not options.dryrun:
        webbrowser.open_new('https://account.microsoft.com/rewards')

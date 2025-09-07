import os
import socket

import psutil
import requests
import smbus2 as smbus
from PIL import Image, ImageDraw, ImageFont

from . import SSD1306

show = SSD1306.SSD1306()
show.Init()
dir_path = os.path.dirname(os.path.abspath(__file__))


font = ImageFont.truetype(dir_path + "/Courier_New.ttf", 13)

image1 = Image.new("1", (show.width, show.height), "WHITE")
draw = ImageDraw.Draw(image1)


class POE_HAT_B:
    def __init__(self, address=0x20):
        self.i2c = smbus.SMBus(1)
        self.address = address  # 0x20
        self.FAN_ON()
        self.FAN_MODE = 0

    def FAN_ON(self):
        self.i2c.write_byte(self.address, 0xFE & self.i2c.read_byte(self.address))

    def FAN_OFF(self):
        self.i2c.write_byte(self.address, 0x01 | self.i2c.read_byte(self.address))

    def GET_IP(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip

    def GET_Temp(self):
        with open("/sys/class/thermal/thermal_zone0/temp", "rt") as f:
            temp = (int)(f.read()) / 1000.0
        return temp

    def GET_CPU_Usage(self):
        return psutil.cpu_percent(interval=0.1)

    def GET_Pihole_Stats(self):
        try:
            # Try Pi-hole API endpoint
            url = "http://localhost/api/stats/summary"
            response = requests.get(url, timeout=2)
            data = response.json()

            queries_today = data["queries"]["total"]
            ads_blocked_today = data["queries"]["blocked"]
            ads_percentage_today = data["queries"]["percent_blocked"]

            return queries_today, ads_blocked_today, ads_percentage_today
        except:
            # Fallback values if API fails
            return 0, 0, 0

    def format_number(self, num):
        """Format numbers in K format for display"""
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return str(num)

    def POE_HAT_Display(self, FAN_TEMP):
        image1 = Image.new("1", (show.width, show.height), "WHITE")
        draw = ImageDraw.Draw(image1)

        # Get system stats
        temp = self.GET_Temp()
        cpu_usage = self.GET_CPU_Usage()

        # Get Pi-hole stats
        total_queries, blocked_queries, block_percentage = self.GET_Pihole_Stats()

        # Determine fan status first for display
        if temp >= FAN_TEMP:
            self.FAN_MODE = 1
        elif temp < FAN_TEMP - 2:
            self.FAN_MODE = 0

        fan_status = "Y" if self.FAN_MODE == 1 else "N"

        # Format the display strings
        # Line 1: blocked/total percentage (format: 1.2K/5.6K 22%)
        blocked_str = self.format_number(blocked_queries)
        total_str = self.format_number(total_queries)
        line1 = f"{blocked_str}/{total_str} {int(block_percentage)}%"

        # Line 2: Temperature, CPU, and Fan (format: T:40.5 C:15% F:N)
        line2 = f"T:{temp:.1f} C:{int(cpu_usage)}% F:{fan_status}"

        # Draw the text
        draw.text((0, 1), line1, font=font, fill=0)
        draw.text((0, 15), line2, font=font, fill=0)

        # Control the fan based on determined status
        if self.FAN_MODE == 1:
            self.FAN_ON()
        else:
            self.FAN_OFF()

        show.ShowImage(show.getbuffer(image1))

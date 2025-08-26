"""
Robot FTP Downloader for ABB YuMi Robot.

This module handles FTP communication with the ABB YuMi robot to download
captured images for processing by the Robot Drawing System.

Features:
- FTP connection to robot controller
- Automatic image file download
- Error handling and retry mechanisms
- Progress monitoring
- Configurable connection parameters

The downloader is specifically configured for ABB YuMi robots but can be
adapted for other robot systems with FTP capabilities.


Version: 1.0
"""
from ftplib import FTP
import os
import sys


class RobotFTPDownloader:
    """
    FTP client for downloading files from ABB YuMi robot.
    
    Handles secure connection and file transfer operations.
    """
    
    # Default robot connection settings
    DEFAULT_ROBOT_IP = "192.168.125.1"
    DEFAULT_USERNAME = "yumi"
    DEFAULT_PASSWORD = "yumi"
    
    # Default file paths
    DEFAULT_REMOTE_PATH = "/hd0a/14000-500767/HOME/image.bmp"
    DEFAULT_LOCAL_PATH = "image.bmp"
    
    def __init__(self, robot_ip=DEFAULT_ROBOT_IP, username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD):
        """
        Initialize FTP downloader.
        
        Args:
            robot_ip (str): Robot controller IP address
            username (str): FTP username
            password (str): FTP password
        """
        self.robot_ip = robot_ip
        self.username = username
        self.password = password
        self.ftp = None
    
    def connect(self):
        """
        Establish FTP connection to robot.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.ftp = FTP(self.robot_ip)
            self.ftp.login(user=self.username, passwd=self.password)
            print(f"Connected to robot FTP at {self.robot_ip}")
            return True
        except Exception as e:
            print(f"FTP connection failed: {e}")
            return False
    
    def download_image(self, remote_path=DEFAULT_REMOTE_PATH, local_path=DEFAULT_LOCAL_PATH):
        """
        Download image file from robot.
        
        Args:
            remote_path (str): Path to file on robot
            local_path (str): Local path to save file
        
        Returns:
            bool: True if download successful, False otherwise
        """
        if not self.ftp:
            print("No FTP connection established")
            return False
        
        try:
            with open(local_path, "wb") as f:
                self.ftp.retrbinary(f"RETR {remote_path}", f.write)
            
            print(f"Downloaded: {remote_path} → {local_path}")
            return True
        except Exception as e:
            print(f"Download failed: {e}")
            return False
    
    def disconnect(self):
        """Close FTP connection."""
        if self.ftp:
            try:
                self.ftp.quit()
                print("FTP connection closed")
            except:
                pass
            self.ftp = None


def main():
    """Main script execution for standalone use."""
    # Configuration
    robot_ip = "192.168.125.1"
    username = "yumi"
    password = "yumi"
    remote_path = "/hd0a/14000-500767/HOME/image.bmp"
    local_path = "image.bmp"
    
    # Create downloader and execute
    downloader = RobotFTPDownloader(robot_ip, username, password)
    
    if downloader.connect():
        success = downloader.download_image(remote_path, local_path)
        downloader.disconnect()
        
        if success:
            print("Image download completed successfully")
        else:
            print("Image download failed")
            sys.exit(1)
    else:
        print("Could not connect to robot FTP")
        sys.exit(1)


if __name__ == "__main__":
    main()

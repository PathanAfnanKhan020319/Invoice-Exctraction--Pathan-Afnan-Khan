"""
Google Drive integration for downloading invoices
"""

import os
import io
from typing import List
from pathlib import Path
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

# Scopes for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class GoogleDriveLoader:
    """
    Download invoice files from Google Drive
    """
    
    def __init__(self, credentials_path: str = "credentials.json"):
        """
        Initialize Google Drive loader
        
        Args:
            credentials_path: Path to credentials JSON file from Google Cloud Console
        """
        self.credentials_path = credentials_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        token_path = 'token.json'
        
        # Check if token already exists
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_path}\n"
                        "Please download it from Google Cloud Console"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for future use
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        # Build service
        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Google Drive authenticated successfully")
    
    def list_files_in_folder(self, folder_id: str) -> List[dict]:
        """
        List all files in a Google Drive folder
        
        Args:
            folder_id: Google Drive folder ID
        
        Returns:
            List of file metadata dictionaries
        """
        try:
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id, name, mimeType, size, createdTime)",
                pageSize=1000
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} files in folder {folder_id}")
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def download_file(self, file_id: str, file_name: str, output_dir: str = "data/raw") -> str:
        """
        Download a file from Google Drive
        
        Args:
            file_id: Google Drive file ID
            file_name: Name to save file as
            output_dir: Directory to save file
        
        Returns:
            Path to downloaded file
        """
        try:
            # Create output directory
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Download file
            request = self.service.files().get_media(fileId=file_id)
            
            output_path = os.path.join(output_dir, file_name)
            
            with io.FileIO(output_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.debug(f"Download {int(status.progress() * 100)}%")
            
            logger.info(f"Downloaded {file_name} to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading file {file_name}: {e}")
            return None
    
    def download_folder(
        self, 
        folder_id: str, 
        output_dir: str = "data/raw",
        supported_formats: List[str] = None
    ) -> List[str]:
        """
        Download all supported files from a Google Drive folder
        
        Args:
            folder_id: Google Drive folder ID
            output_dir: Directory to save files
            supported_formats: List of file extensions to download
        
        Returns:
            List of paths to downloaded files
        """
        if supported_formats is None:
            supported_formats = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff']
        
        # Get list of files
        files = self.list_files_in_folder(folder_id)
        
        # Filter supported formats
        invoice_files = [
            f for f in files 
            if any(f['name'].lower().endswith(fmt) for fmt in supported_formats)
        ]
        
        logger.info(f"Found {len(invoice_files)} invoice files to download")
        
        # Download each file
        downloaded_paths = []
        
        for file in invoice_files:
            file_path = self.download_file(file['id'], file['name'], output_dir)
            if file_path:
                downloaded_paths.append(file_path)
        
        logger.info(f"Successfully downloaded {len(downloaded_paths)} files")
        return downloaded_paths
    
    def get_folder_id_from_url(self, url: str) -> str:
        """
        Extract folder ID from Google Drive URL
        
        Args:
            url: Google Drive folder URL
        
        Returns:
            Folder ID
        """
        # Handle different URL formats
        if '/folders/' in url:
            folder_id = url.split('/folders/')[1].split('?')[0]
        elif 'id=' in url:
            folder_id = url.split('id=')[1].split('&')[0]
        else:
            folder_id = url  # Assume it's already an ID
        
        return folder_id
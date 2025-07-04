# AWS Integration Utilities
# app/aws_utils.py

import boto3
import os
import json
import logging
from datetime import datetime, timezone
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, Dict, Any, List
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class S3Manager:
    """Manages S3 operations for SeeHearAI"""
    
    def __init__(self):
        self.bucket_name = os.getenv("S3_BUCKET","seehearai-storage-1751154579")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        if not self.bucket_name:
            logger.error("S3_BUCKET environment variable not set")
            raise ValueError("S3_BUCKET environment variable is required")
        
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
            self.s3_resource = boto3.resource('s3', region_name=self.region)
            self.bucket = self.s3_resource.Bucket(self.bucket_name)
            logger.info(f"S3Manager initialized for bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test S3 connection"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except Exception as e:
            logger.error(f"S3 connection test failed: {e}")
            return False
    
    async def upload_file_bytes(self, file_bytes: bytes, key: str, content_type: str = None) -> bool:
        """Upload file bytes to S3 asynchronously"""
        try:
            def _upload():
                extra_args = {}
                if content_type:
                    extra_args['ContentType'] = content_type
                
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=file_bytes,
                    **extra_args
                )
                return True
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, _upload)
            
            logger.info(f"File uploaded to S3: s3://{self.bucket_name}/{key}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            return False
    
    def upload_file(self, file_path: str, key: str, content_type: str = None) -> bool:
        """Upload file to S3"""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.upload_file(file_path, self.bucket_name, key, ExtraArgs=extra_args)
            logger.info(f"File uploaded: {file_path} -> s3://{self.bucket_name}/{key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {e}")
            return False
    
    def download_file(self, key: str, file_path: str) -> bool:
        """Download file from S3"""
        try:
            self.s3_client.download_file(self.bucket_name, key, file_path)
            logger.info(f"File downloaded: s3://{self.bucket_name}/{key} -> {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download file {key}: {e}")
            return False
    
    def get_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """Generate presigned URL for S3 object"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            return None
    
    def delete_file(self, key: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"File deleted: s3://{self.bucket_name}/{key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {key}: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> List[str]:
        """List files in S3 bucket with optional prefix"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                files = [obj['Key'] for obj in response['Contents']]
            
            return files
        except Exception as e:
            logger.error(f"Failed to list files with prefix {prefix}: {e}")
            return []
    
    def get_file_url(self, key: str) -> str:
        """Get public URL for S3 object (if bucket is public)"""
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"


class DynamoDBManager:
    """Manages DynamoDB operations for SeeHearAI"""
    
    def __init__(self):
        self.table_name = os.getenv("DYNAMODB_TABLE", "SeeHearAISessions")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
            self.table = self.dynamodb.Table(self.table_name)
            logger.info(f"DynamoDBManager initialized for table: {self.table_name}")
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test DynamoDB connection"""
        try:
            self.table.table_status
            return True
        except Exception as e:
            logger.error(f"DynamoDB connection test failed: {e}")
            return False
    
    def log_session_event(self, session_id: str, event_type: str, data: Dict[Any, Any]) -> bool:
        """Log an event for a session"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            item = {
                'session_id': session_id,
                'timestamp': timestamp,
                'event_type': event_type,
                'data': data,
                'ttl': int((datetime.now(timezone.utc).timestamp() + 2592000))  # 30 days TTL
            }
            
            self.table.put_item(Item=item)
            logger.debug(f"Event logged: {session_id} - {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log session event: {e}")
            return False
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all events for a session"""
        try:
            response = self.table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('session_id').eq(session_id),
                ScanIndexForward=True  # Sort by timestamp ascending
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"Failed to get session history for {session_id}: {e}")
            return []
    
    def get_recent_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent sessions"""
        try:
            # This would require a GSI on timestamp for efficient querying
            # For now, we'll scan with a limit (not ideal for production)
            response = self.table.scan(
                Limit=limit,
                FilterExpression=boto3.dynamodb.conditions.Attr('event_type').eq('session_start')
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"Failed to get recent sessions: {e}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """Delete all events for a session"""
        try:
            # Get all items for the session
            response = self.table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('session_id').eq(session_id)
            )
            
            # Delete each item
            with self.table.batch_writer() as batch:
                for item in response.get('Items', []):
                    batch.delete_item(
                        Key={
                            'session_id': item['session_id'],
                            'timestamp': item['timestamp']
                        }
                    )
            
            logger.info(f"Session deleted: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def get_user_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get analytics for a session"""
        try:
            events = self.get_session_history(session_id)
            
            analytics = {
                'total_events': len(events),
                'session_duration': 0,
                'questions_asked': 0,
                'hotword_detections': 0,
                'vision_analyses': 0,
                'errors': 0
            }
            
            if not events:
                return analytics
            
            # Calculate session duration
            start_time = None
            end_time = None
            
            for event in events:
                event_time = datetime.fromisoformat(event['timestamp'])
                
                if event['event_type'] == 'session_start':
                    start_time = event_time
                
                if start_time and not end_time:
                    end_time = event_time
                
                # Count event types
                if event['event_type'] == 'qa_interaction':
                    analytics['questions_asked'] += 1
                elif event['event_type'] == 'speech_input' and 'hotword' in event.get('data', {}).get('processed_text', ''):
                    analytics['hotword_detections'] += 1
                elif event['event_type'] == 'vision_analysis':
                    analytics['vision_analyses'] += 1
                elif 'error' in event['event_type'].lower():
                    analytics['errors'] += 1
            
            if start_time and end_time:
                analytics['session_duration'] = (end_time - start_time).total_seconds()
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get analytics for session {session_id}: {e}")
            return {}


class CloudWatchLogger:
    """CloudWatch logging for SeeHearAI metrics"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch', region_name=os.getenv("AWS_REGION", "us-east-1"))
        self.namespace = "SeeHearAI"
    
    def log_metric(self, metric_name: str, value: float, unit: str = "Count", dimensions: Dict[str, str] = None):
        """Log a custom metric to CloudWatch"""
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.now(timezone.utc)
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            
            logger.debug(f"Metric logged: {metric_name} = {value}")
            
        except Exception as e:
            logger.error(f"Failed to log metric {metric_name}: {e}")
    
    def log_response_time(self, operation: str, duration: float):
        """Log response time metric"""
        self.log_metric(f"{operation}_ResponseTime", duration, "Seconds")
    
    def log_error(self, error_type: str):
        """Log error metric"""
        self.log_metric(f"Error_{error_type}", 1.0, "Count")
    
    def log_user_interaction(self, interaction_type: str):
        """Log user interaction metric"""
        self.log_metric(f"UserInteraction_{interaction_type}", 1.0, "Count")
import json
import boto3
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
import re
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

# Configuration
SOURCE_TABLE = 'SeeHearAISessions'
S3_BUCKET = 'seehearai-storage-1751154579'
ANALYTICS_PREFIX = 'analytics'

def lambda_handler(event, context):
    """
    ETL Pipeline for SeeHearAI Data
    Extract from DynamoDB + S3, Transform, Load to S3 Analytics
    """
    try:
        # Step 1: Extract session data
        session_data = extract_session_data()
        
        # Step 2: Extract multimedia data metrics
        multimedia_metrics = extract_multimedia_metrics()
        
        # Step 3: Transform and analyze
        analytics_results = transform_and_analyze(session_data, multimedia_metrics)
        
        # Step 4: Load to S3 analytics layer
        load_analytics_results(analytics_results)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'ETL pipeline completed successfully',
                'processed_sessions': len(session_data),
                'analytics_generated': len(analytics_results)
            })
        }
        
    except Exception as e:
        logger.error(f"ETL pipeline failed: {str(e)}")
        raise

def extract_session_data():
    """Extract all session data from DynamoDB"""
    table = dynamodb.Table(SOURCE_TABLE)
    
    response = table.scan()
    items = response['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])
    
    logger.info(f"Extracted {len(items)} session events")
    return items

def extract_multimedia_metrics():
    """Extract multimedia file metrics from S3"""
    metrics = {
        'audio_files': [],
        'video_frames': [],
        'total_storage': 0
    }
    
    # Get audio files metrics
    audio_response = s3_client.list_objects_v2(
        Bucket=S3_BUCKET,
        Prefix='audio-files/'
    )
    
    if 'Contents' in audio_response:
        for obj in audio_response['Contents']:
            if obj['Key'].endswith('.mp3'):
                metrics['audio_files'].append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'session_id': extract_session_id_from_path(obj['Key'])
                })
                metrics['total_storage'] += obj['Size']
    
    # Get video frames metrics
    video_response = s3_client.list_objects_v2(
        Bucket=S3_BUCKET,
        Prefix='video-frames/'
    )
    
    if 'Contents' in video_response:
        for obj in video_response['Contents']:
            if obj['Key'].endswith('.jpg'):
                metrics['video_frames'].append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'session_id': extract_session_id_from_path(obj['Key'])
                })
                metrics['total_storage'] += obj['Size']
    
    logger.info(f"Extracted metrics for {len(metrics['audio_files'])} audio files and {len(metrics['video_frames'])} video frames")
    return metrics

def transform_and_analyze(session_data, multimedia_metrics):
    """Transform raw data into analytics insights"""
    
    # Group events by session
    sessions_grouped = defaultdict(list)
    for event in session_data:
        sessions_grouped[event['session_id']].append(event)
    
    analytics = {
        'session_analytics': analyze_sessions(sessions_grouped),
        'user_interaction_patterns': analyze_interaction_patterns(session_data),
        'vision_analysis_insights': analyze_vision_data(session_data),
        'multimedia_analytics': analyze_multimedia_usage(multimedia_metrics),
        'performance_metrics': calculate_performance_metrics(session_data, multimedia_metrics),
        'daily_usage_stats': calculate_daily_stats(session_data),
        'ai_accuracy_metrics': analyze_ai_accuracy(session_data)
    }
    
    return analytics

def analyze_sessions(sessions_grouped):
    """Analyze session-level metrics"""
    session_analytics = []
    
    for session_id, events in sessions_grouped.items():
        # Sort events by timestamp
        events.sort(key=lambda x: x['timestamp'])
        
        session_start = None
        session_end = None
        event_counts = defaultdict(int)
        
        for event in events:
            event_counts[event['event_type']] += 1
            
            if event['event_type'] == 'session_start':
                session_start = event['timestamp']
            
            session_end = event['timestamp']  # Last event timestamp
        
        # Calculate session duration
        duration_seconds = 0
        if session_start and session_end and session_start != session_end:
            start_dt = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(session_end.replace('Z', '+00:00'))
            duration_seconds = (end_dt - start_dt).total_seconds()
        
        session_analytics.append({
            'session_id': session_id,
            'duration_seconds': duration_seconds,
            'total_events': len(events),
            'event_breakdown': dict(event_counts),
            'has_vision_analysis': 'vision_analysis' in event_counts,
            'has_speech_input': 'speech_input' in event_counts,
            'engagement_score': calculate_engagement_score(event_counts, duration_seconds)
        })
    
    return session_analytics

def analyze_interaction_patterns(session_data):
    """Analyze user interaction patterns"""
    patterns = {
        'most_common_event_types': defaultdict(int),
        'average_events_per_session': 0,
        'peak_usage_hours': defaultdict(int),
        'user_journey_flows': analyze_user_journeys(session_data)
    }
    
    total_events = len(session_data)
    sessions = set()
    
    for event in session_data:
        patterns['most_common_event_types'][event['event_type']] += 1
        sessions.add(event['session_id'])
        
        # Extract hour from timestamp
        timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
        hour = timestamp.hour
        patterns['peak_usage_hours'][hour] += 1
    
    patterns['average_events_per_session'] = total_events / len(sessions) if sessions else 0
    
    return patterns

def analyze_vision_data(session_data):
    """Analyze vision analysis results"""
    vision_events = [e for e in session_data if e['event_type'] == 'vision_analysis']
    
    insights = {
        'total_vision_analyses': len(vision_events),
        'detected_objects': defaultdict(int),
        'common_scenes': defaultdict(int),
        'analysis_length_stats': []
    }
    
    for event in vision_events:
        analysis_text = event.get('data', {}).get('analysis', '')
        insights['analysis_length_stats'].append(len(analysis_text))
        
        # Extract detected objects
        if 'Detected objects:' in analysis_text:
            objects_part = analysis_text.split('Detected objects:')[1]
            objects = [obj.strip() for obj in objects_part.split(',')]
            for obj in objects:
                if obj:
                    insights['detected_objects'][obj.strip('.')] += 1
        
        # Categorize scenes
        if 'mirror' in analysis_text.lower():
            insights['common_scenes']['indoor_mirror'] += 1
        elif 'person' in analysis_text.lower():
            insights['common_scenes']['person_detected'] += 1
    
    # Calculate statistics
    if insights['analysis_length_stats']:
        insights['avg_analysis_length'] = sum(insights['analysis_length_stats']) / len(insights['analysis_length_stats'])
        insights['max_analysis_length'] = max(insights['analysis_length_stats'])
        insights['min_analysis_length'] = min(insights['analysis_length_stats'])
    
    return insights

def analyze_multimedia_usage(multimedia_metrics):
    """Analyze multimedia file usage patterns"""
    analytics = {
        'storage_breakdown': {
            'total_storage_bytes': multimedia_metrics['total_storage'],
            'total_storage_mb': round(multimedia_metrics['total_storage'] / 1024 / 1024, 2),
            'audio_files_count': len(multimedia_metrics['audio_files']),
            'video_frames_count': len(multimedia_metrics['video_frames'])
        },
        'file_size_analytics': {},
        'session_multimedia_mapping': {}
    }
    
    # Analyze file sizes
    audio_sizes = [f['size'] for f in multimedia_metrics['audio_files']]
    video_sizes = [f['size'] for f in multimedia_metrics['video_frames']]
    
    if audio_sizes:
        analytics['file_size_analytics']['audio'] = {
            'avg_size_kb': round(sum(audio_sizes) / len(audio_sizes) / 1024, 2),
            'max_size_kb': round(max(audio_sizes) / 1024, 2),
            'min_size_kb': round(min(audio_sizes) / 1024, 2)
        }
    
    if video_sizes:
        analytics['file_size_analytics']['video'] = {
            'avg_size_kb': round(sum(video_sizes) / len(video_sizes) / 1024, 2),
            'max_size_kb': round(max(video_sizes) / 1024, 2),
            'min_size_kb': round(min(video_sizes) / 1024, 2)
        }
    
    return analytics

def calculate_performance_metrics(session_data, multimedia_metrics):
    """Calculate system performance metrics"""
    
    # Group events by session to calculate processing times
    sessions = defaultdict(list)
    for event in session_data:
        sessions[event['session_id']].append(event)
    
    performance = {
        'avg_session_duration': 0,
        'response_time_analysis': {},
        'throughput_metrics': {
            'events_per_hour': 0,
            'vision_analyses_per_hour': 0
        },
        'storage_efficiency': {
            'storage_per_session': 0,
            'compression_ratio': 0
        }
    }
    
    # Calculate session durations
    session_durations = []
    for session_id, events in sessions.items():
        if len(events) > 1:
            events.sort(key=lambda x: x['timestamp'])
            start_time = datetime.fromisoformat(events[0]['timestamp'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(events[-1]['timestamp'].replace('Z', '+00:00'))
            duration = (end_time - start_time).total_seconds()
            session_durations.append(duration)
    
    if session_durations:
        performance['avg_session_duration'] = sum(session_durations) / len(session_durations)
    
    # Calculate throughput
    if session_data:
        total_hours = 24  # Assuming data spans roughly a day based on timestamps
        performance['throughput_metrics']['events_per_hour'] = len(session_data) / total_hours
        
        vision_events = len([e for e in session_data if e['event_type'] == 'vision_analysis'])
        performance['throughput_metrics']['vision_analyses_per_hour'] = vision_events / total_hours
    
    return performance

def calculate_daily_stats(session_data):
    """Calculate daily usage statistics"""
    daily_stats = defaultdict(lambda: {
        'total_events': 0,
        'unique_sessions': set(),
        'event_types': defaultdict(int)
    })
    
    for event in session_data:
        timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
        date_key = timestamp.strftime('%Y-%m-%d')
        
        daily_stats[date_key]['total_events'] += 1
        daily_stats[date_key]['unique_sessions'].add(event['session_id'])
        daily_stats[date_key]['event_types'][event['event_type']] += 1
    
    # Convert sets to counts
    for date, stats in daily_stats.items():
        stats['unique_sessions'] = len(stats['unique_sessions'])
        stats['event_types'] = dict(stats['event_types'])
    
    return dict(daily_stats)

def analyze_ai_accuracy(session_data):
    """Analyze AI model accuracy and performance"""
    vision_events = [e for e in session_data if e['event_type'] == 'vision_analysis']
    speech_events = [e for e in session_data if e['event_type'] == 'speech_input']
    
    accuracy_metrics = {
        'vision_model_performance': {
            'total_analyses': len(vision_events),
            'object_detection_rate': 0,
            'scene_description_completeness': 0
        },
        'speech_model_performance': {
            'total_speech_inputs': len(speech_events),
            'processing_accuracy': 0
        }
    }
    
    # Analyze vision accuracy
    objects_detected = 0
    for event in vision_events:
        analysis = event.get('data', {}).get('analysis', '')
        if 'Detected objects:' in analysis:
            objects_detected += 1
    
    if vision_events:
        accuracy_metrics['vision_model_performance']['object_detection_rate'] = objects_detected / len(vision_events)
    
    return accuracy_metrics

def analyze_user_journeys(session_data):
    """Analyze typical user journey patterns"""
    journeys = defaultdict(list)
    
    # Group by session and sort by timestamp
    sessions = defaultdict(list)
    for event in session_data:
        sessions[event['session_id']].append(event)
    
    for session_id, events in sessions.items():
        events.sort(key=lambda x: x['timestamp'])
        journey = [event['event_type'] for event in events]
        journey_key = ' -> '.join(journey)
        journeys[journey_key].append(session_id)
    
    return dict(journeys)

def calculate_engagement_score(event_counts, duration_seconds):
    """Calculate user engagement score"""
    base_score = len(event_counts)  # Variety of interactions
    
    # Bonus for vision analysis
    if 'vision_analysis' in event_counts:
        base_score += event_counts['vision_analysis'] * 2
    
    # Bonus for speech input
    if 'speech_input' in event_counts:
        base_score += event_counts['speech_input'] * 1.5
    
    # Duration factor (longer sessions get higher scores)
    if duration_seconds > 30:  # Sessions longer than 30 seconds
        base_score *= 1.5
    
    return round(base_score, 2)

def extract_session_id_from_path(s3_key):
    """Extract session ID from S3 object path"""
    # Pattern: folder/session-id/filename
    parts = s3_key.split('/')
    if len(parts) >= 2:
        return parts[1]  # Session ID should be the second part
    return None

def load_analytics_results(analytics_results):
    """Load analytics results to S3"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Upload main analytics report
    analytics_key = f"{ANALYTICS_PREFIX}/daily_analytics/{timestamp}_analytics_report.json"
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=analytics_key,
        Body=json.dumps(analytics_results, indent=2, default=str),
        ContentType='application/json'
    )
    
    # Upload individual analytics components
    for component_name, component_data in analytics_results.items():
        component_key = f"{ANALYTICS_PREFIX}/components/{component_name}/{timestamp}_{component_name}.json"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=component_key,
            Body=json.dumps(component_data, indent=2, default=str),
            ContentType='application/json'
        )
    
    logger.info(f"Analytics results uploaded to {analytics_key}")
    
    return analytics_key
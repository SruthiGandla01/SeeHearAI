import json
import boto3
from datetime import datetime, timedelta
import logging
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

S3_BUCKET = 'seehearai-storage-1751154579'

def lambda_handler(event, context):
    """
    Analytics Dashboard API
    Returns formatted analytics data for dashboard visualization
    """
    try:
        # Get the latest analytics report
        latest_analytics = get_latest_analytics()
        
        # Format for dashboard
        dashboard_data = format_dashboard_data(latest_analytics)
        
        # Generate HTML dashboard if requested
        if event.get('generate_html', False):
            html_dashboard = generate_html_dashboard(dashboard_data)
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/html',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': html_dashboard
            }
        
        # Return JSON data
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(dashboard_data, default=str)
        }
        
    except Exception as e:
        logger.error(f"Dashboard API error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_latest_analytics():
    """Get the most recent analytics report from S3"""
    try:
        # List analytics reports
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix='analytics/daily_analytics/',
            Delimiter='/'
        )
        
        if 'Contents' not in response:
            raise Exception("No analytics reports found")
        
        # Get the most recent report
        latest_file = max(response['Contents'], key=lambda x: x['LastModified'])
        
        # Download and parse the report
        report_response = s3_client.get_object(
            Bucket=S3_BUCKET,
            Key=latest_file['Key']
        )
        
        analytics_data = json.loads(report_response['Body'].read().decode('utf-8'))
        
        return analytics_data
        
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        raise

def format_dashboard_data(analytics):
    """Format analytics data for dashboard visualization"""
    
    dashboard = {
        'summary': {
            'total_sessions': len(analytics.get('session_analytics', [])),
            'total_events': sum([session.get('total_events', 0) for session in analytics.get('session_analytics', [])]),
            'avg_session_duration': calculate_avg_session_duration(analytics.get('session_analytics', [])),
            'top_interaction_type': get_top_interaction_type(analytics.get('user_interaction_patterns', {}))
        },
        'charts': {
            'session_engagement': format_session_engagement_chart(analytics.get('session_analytics', [])),
            'interaction_patterns': format_interaction_patterns_chart(analytics.get('user_interaction_patterns', {})),
            'vision_insights': format_vision_insights_chart(analytics.get('vision_analysis_insights', {})),
            'usage_over_time': format_usage_timeline_chart(analytics.get('daily_usage_stats', {})),
            'performance_metrics': format_performance_chart(analytics.get('performance_metrics', {}))
        },
        'insights': {
            'key_findings': generate_key_insights(analytics),
            'recommendations': generate_recommendations(analytics)
        },
        'raw_data': analytics,
        'last_updated': datetime.now().isoformat()
    }
    
    return dashboard

def calculate_avg_session_duration(sessions):
    """Calculate average session duration"""
    if not sessions:
        return 0
    
    durations = [session.get('duration_seconds', 0) for session in sessions]
    return round(sum(durations) / len(durations), 2) if durations else 0

def get_top_interaction_type(patterns):
    """Get the most common interaction type"""
    event_types = patterns.get('most_common_event_types', {})
    if not event_types:
        return 'No interactions'
    
    return max(event_types.keys(), key=lambda k: event_types[k])

def format_session_engagement_chart(sessions):
    """Format session data for engagement chart"""
    if not sessions:
        return {'labels': [], 'data': []}
    
    # Create engagement score distribution
    engagement_ranges = {'Low (0-5)': 0, 'Medium (5-10)': 0, 'High (10+)': 0}
    
    for session in sessions:
        score = session.get('engagement_score', 0)
        if score < 5:
            engagement_ranges['Low (0-5)'] += 1
        elif score < 10:
            engagement_ranges['Medium (5-10)'] += 1
        else:
            engagement_ranges['High (10+)'] += 1
    
    return {
        'labels': list(engagement_ranges.keys()),
        'data': list(engagement_ranges.values()),
        'type': 'pie'
    }

def format_interaction_patterns_chart(patterns):
    """Format interaction patterns for chart"""
    event_types = patterns.get('most_common_event_types', {})
    
    return {
        'labels': list(event_types.keys()),
        'data': list(event_types.values()),
        'type': 'bar'
    }

def format_vision_insights_chart(vision_data):
    """Format vision analysis insights for chart"""
    detected_objects = vision_data.get('detected_objects', {})
    
    # Get top 10 most detected objects
    sorted_objects = sorted(detected_objects.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'labels': [obj[0] for obj in sorted_objects],
        'data': [obj[1] for obj in sorted_objects],
        'type': 'bar'
    }

def format_usage_timeline_chart(daily_stats):
    """Format daily usage stats for timeline chart"""
    if not daily_stats:
        return {'labels': [], 'data': []}
    
    # Sort by date
    sorted_dates = sorted(daily_stats.keys())
    
    return {
        'labels': sorted_dates,
        'data': [daily_stats[date].get('total_events', 0) for date in sorted_dates],
        'type': 'line'
    }

def format_performance_chart(performance):
    """Format performance metrics for chart"""
    throughput = performance.get('throughput_metrics', {})
    
    return {
        'labels': ['Events/Hour', 'Vision Analyses/Hour'],
        'data': [
            throughput.get('events_per_hour', 0),
            throughput.get('vision_analyses_per_hour', 0)
        ],
        'type': 'bar'
    }

def generate_key_insights(analytics):
    """Generate key insights from analytics data"""
    insights = []
    
    sessions = analytics.get('session_analytics', [])
    vision_data = analytics.get('vision_analysis_insights', {})
    patterns = analytics.get('user_interaction_patterns', {})
    
    # Session insights
    if sessions:
        total_sessions = len(sessions)
        avg_duration = calculate_avg_session_duration(sessions)
        insights.append(f"📊 Analyzed {total_sessions} user sessions with average duration of {avg_duration:.1f} seconds")
        
        # Engagement insights
        high_engagement = len([s for s in sessions if s.get('engagement_score', 0) > 10])
        if high_engagement > 0:
            engagement_rate = (high_engagement / total_sessions) * 100
            insights.append(f"🔥 {engagement_rate:.1f}% of sessions show high user engagement")
    
    # Vision insights
    total_analyses = vision_data.get('total_vision_analyses', 0)
    if total_analyses > 0:
        insights.append(f"👁️ Processed {total_analyses} vision analyses with AI object detection")
        
        detected_objects = vision_data.get('detected_objects', {})
        if detected_objects:
            top_object = max(detected_objects.keys(), key=lambda k: detected_objects[k])
            insights.append(f"🎯 Most frequently detected object: '{top_object}' ({detected_objects[top_object]} times)")
    
    # Usage patterns
    peak_hours = patterns.get('peak_usage_hours', {})
    if peak_hours:
        peak_hour = max(peak_hours.keys(), key=lambda k: peak_hours[k])
        insights.append(f"⏰ Peak usage occurs at hour {peak_hour}:00")
    
    # Performance insights
    performance = analytics.get('performance_metrics', {})
    avg_session_duration = performance.get('avg_session_duration', 0)
    if avg_session_duration > 0:
        insights.append(f"⚡ Average session duration: {avg_session_duration:.1f} seconds")
    
    return insights

def generate_recommendations(analytics):
    """Generate actionable recommendations"""
    recommendations = []
    
    sessions = analytics.get('session_analytics', [])
    vision_data = analytics.get('vision_analysis_insights', {})
    performance = analytics.get('performance_metrics', {})
    
    # Session recommendations
    if sessions:
        low_engagement = len([s for s in sessions if s.get('engagement_score', 0) < 5])
        if low_engagement > len(sessions) * 0.3:  # More than 30% low engagement
            recommendations.append("💡 Consider adding interactive features to increase user engagement")
    
    # Vision recommendations
    detection_rate = vision_data.get('total_vision_analyses', 0)
    if detection_rate > 0:
        avg_objects = sum(vision_data.get('detected_objects', {}).values()) / detection_rate
        if avg_objects < 2:
            recommendations.append("🔍 Consider improving object detection accuracy or expanding model capabilities")
    
    # Performance recommendations
    throughput = performance.get('throughput_metrics', {})
    events_per_hour = throughput.get('events_per_hour', 0)
    if events_per_hour > 50:
        recommendations.append("🚀 High usage detected - consider implementing caching or scaling strategies")
    
    # Storage recommendations
    multimedia = analytics.get('multimedia_analytics', {})
    storage_mb = multimedia.get('storage_breakdown', {}).get('total_storage_mb', 0)
    if storage_mb > 100:
        recommendations.append("💾 Consider implementing data archival or compression for multimedia files")
    
    return recommendations

def generate_html_dashboard(dashboard_data):
    """Generate HTML dashboard"""
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SeeHearAI Analytics Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; 
                padding: 20px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
            }}
            .container {{ 
                max-width: 1200px; 
                margin: 0 auto; 
                background: white; 
                border-radius: 15px; 
                padding: 30px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }}
            .header {{ 
                text-align: center; 
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 3px solid #667eea;
            }}
            .header h1 {{ 
                color: #667eea; 
                margin: 0;
                font-size: 2.5em;
                font-weight: 300;
            }}
            .header p {{ 
                color: #666; 
                margin: 10px 0 0 0;
                font-size: 1.1em;
            }}
            .summary {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                gap: 20px; 
                margin-bottom: 40px; 
            }}
            .summary-card {{ 
                background: linear-gradient(135deg, #667eea, #764ba2); 
                color: white; 
                padding: 25px; 
                border-radius: 12px; 
                text-align: center;
                transform: translateY(0);
                transition: transform 0.3s ease;
            }}
            .summary-card:hover {{ transform: translateY(-5px); }}
            .summary-card h3 {{ margin: 0 0 10px 0; font-size: 1.2em; opacity: 0.9; }}
            .summary-card .value {{ font-size: 2.5em; font-weight: bold; margin: 0; }}
            .charts {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); 
                gap: 30px; 
                margin-bottom: 40px; 
            }}
            .chart-container {{ 
                background: white; 
                border-radius: 12px; 
                padding: 25px; 
                box-shadow: 0 8px 16px rgba(0,0,0,0.1);
                border: 1px solid #eee;
            }}
            .chart-title {{ 
                font-size: 1.3em; 
                font-weight: 600; 
                margin-bottom: 20px; 
                color: #333; 
                text-align: center;
            }}
            .insights {{ 
                display: grid; 
                grid-template-columns: 1fr 1fr; 
                gap: 30px; 
            }}
            .insights-card {{ 
                background: #f8f9fa; 
                border-radius: 12px; 
                padding: 25px;
                border-left: 5px solid #667eea;
            }}
            .insights-card h3 {{ 
                color: #667eea; 
                margin-top: 0; 
                font-size: 1.3em;
            }}
            .insights-list {{ 
                list-style: none; 
                padding: 0; 
            }}
            .insights-list li {{ 
                margin: 15px 0; 
                padding: 12px; 
                background: white; 
                border-radius: 8px; 
                border-left: 3px solid #28a745;
                font-size: 0.95em;
                line-height: 1.4;
            }}
            .timestamp {{ 
                text-align: center; 
                margin-top: 30px; 
                color: #666; 
                font-style: italic;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }}
            @media (max-width: 768px) {{
                .insights {{ grid-template-columns: 1fr; }}
                .charts {{ grid-template-columns: 1fr; }}
                .summary {{ grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 SeeHearAI Analytics Dashboard</h1>
                <p>Real-time insights from your AI-powered accessibility assistant</p>
            </div>
            
            <div class="summary">
                <div class="summary-card">
                    <h3>Total Sessions</h3>
                    <div class="value">{dashboard_data['summary']['total_sessions']}</div>
                </div>
                <div class="summary-card">
                    <h3>Total Events</h3>
                    <div class="value">{dashboard_data['summary']['total_events']}</div>
                </div>
                <div class="summary-card">
                    <h3>Avg Duration</h3>
                    <div class="value">{dashboard_data['summary']['avg_session_duration']:.1f}s</div>
                </div>
                <div class="summary-card">
                    <h3>Top Interaction</h3>
                    <div class="value" style="font-size: 1.5em;">{dashboard_data['summary']['top_interaction_type']}</div>
                </div>
            </div>
            
            <div class="charts">
                <div class="chart-container">
                    <div class="chart-title">Session Engagement Distribution</div>
                    <canvas id="engagementChart"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-title">Interaction Patterns</div>
                    <canvas id="patternsChart"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-title">Vision Analysis: Detected Objects</div>
                    <canvas id="visionChart"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-title">Usage Over Time</div>
                    <canvas id="usageChart"></canvas>
                </div>
            </div>
            
            <div class="insights">
                <div class="insights-card">
                    <h3>🔍 Key Insights</h3>
                    <ul class="insights-list">
                        {"".join([f"<li>{insight}</li>" for insight in dashboard_data['insights']['key_findings']])}
                    </ul>
                </div>
                <div class="insights-card">
                    <h3>💡 Recommendations</h3>
                    <ul class="insights-list">
                        {"".join([f"<li>{rec}</li>" for rec in dashboard_data['insights']['recommendations']])}
                    </ul>
                </div>
            </div>
            
            <div class="timestamp">
                Last updated: {dashboard_data['last_updated']}
            </div>
        </div>
        
        <script>
            // Chart data
            const chartData = {json.dumps(dashboard_data['charts'])};
            
            // Engagement Chart
            new Chart(document.getElementById('engagementChart'), {{
                type: 'pie',
                data: {{
                    labels: chartData.session_engagement.labels,
                    datasets: [{{
                        data: chartData.session_engagement.data,
                        backgroundColor: ['#ff6384', '#36a2eb', '#4bc0c0']
                    }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false }}
            }});
            
            // Patterns Chart
            new Chart(document.getElementById('patternsChart'), {{
                type: 'bar',
                data: {{
                    labels: chartData.interaction_patterns.labels,
                    datasets: [{{
                        label: 'Count',
                        data: chartData.interaction_patterns.data,
                        backgroundColor: '#667eea'
                    }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false }}
            }});
            
            // Vision Chart
            new Chart(document.getElementById('visionChart'), {{
                type: 'bar',
                data: {{
                    labels: chartData.vision_insights.labels,
                    datasets: [{{
                        label: 'Detections',
                        data: chartData.vision_insights.data,
                        backgroundColor: '#4bc0c0'
                    }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false }}
            }});
            
            // Usage Chart
            new Chart(document.getElementById('usageChart'), {{
                type: 'line',
                data: {{
                    labels: chartData.usage_over_time.labels,
                    datasets: [{{
                        label: 'Events',
                        data: chartData.usage_over_time.data,
                        borderColor: '#ff6384',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        fill: true
                    }}]
                }},
                options: {{ responsive: true, maintainAspectRatio: false }}
            }});
        </script>
    </body>
    </html>
    """
    
    return html_template
import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table_severity = dynamodb.Table('RegionSeverity')

def lambda_handler(event, context):
    try:
        # 1. แกะข้อมูลจาก SNS
        sns_message = event['Records'][0]['Sns']['Message']
        data = json.loads(sns_message)
        
        region = data.get('region')
        severity = data.get('severity')
        
        # 2. บันทึกลงตาราง Severity Cache ของเราเอง
        table_severity.put_item(
            Item={
                'region_name': region,
                'severity_score': Decimal(str(severity)),
                'updated_at': boto3.resource('dynamodb').meta.client.get_waiter('db_exists').waiter_config.get('now', '') # หรือใส่ timestamp ปกติ
            }
        )
        print(f"Updated Cache for {region}: {severity}")
        
    except Exception as e:
        print(f"Error updating cache: {str(e)}")
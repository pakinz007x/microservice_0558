import json
import boto3
import time
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table_data = dynamodb.Table('DisasterRequests')
table_counter = dynamodb.Table('Counters')

def lambda_handler(event, context):
    trace_id = context.aws_request_id
    try:
        body = json.loads(event.get('body', '{}'))
        incident_type = body.get('incident_type', 'General')
        description = body.get('description', 'ไม่มีรายละเอียด')
        latitude = Decimal(str(body.get('latitude', 0.0)))
        longitude = Decimal(str(body.get('longitude', 0.0)))
        
        # 1. รันเลข ID ใหม่จากตาราง Counter
        # ADD 1 ให้กับ last_value และคืนค่าใหม่กลับมาทันที
        counter_response = table_counter.update_item(
            Key={'id_name': 'request_counter'},
            UpdateExpression="ADD last_value :inc",
            ExpressionAttributeValues={':inc': 1},
            ReturnValues="UPDATED_NEW"
        )
        new_count = counter_response['Attributes']['last_value']
        
        # 2. Format ให้เป็น req_001 (03d หมายถึง เลข 3 หลัก เติม 0 ข้างหน้า)
        auto_request_id = f"req_{int(new_count):03d}"
        
        # 3. สร้างเวลาปัจจุบัน
        now = datetime.utcnow().isoformat() + 'Z'
        
        # 4. เตรียมข้อมูลบันทึก
        item = {
            'request_id': auto_request_id,
            'trace_id': trace_id,
            'incident_type': incident_type,
            'description': description,
            'priority_score': Decimal('0'),
            'status': 'New',
            'latitude': latitude,
            'longitude': longitude,
            'reported_time': now,
            'last_updated': now
        }
        
        table_data.put_item(Item=item)

        print(json.dumps({
            "operation": "SUBMIT_REQUEST",
            "request_id": auto_request_id,
            "trace_id": trace_id,
            "status": "SUCCESS"
        }))
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'X-Trace-Id': trace_id
            },
            'body': json.dumps({
                'message': 'บันทึกสำเร็จ',
                'request_id': auto_request_id,
                'trace_id': trace_id
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        print(json.dumps({"operation": "SUBMIT_ERROR", "trace_id": trace_id, "error": str(e)}))
        return {
            'statusCode': 500, 
            'body': json.dumps({'error': str(e), 'trace_id': trace_id})
        }
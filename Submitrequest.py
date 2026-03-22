import json
import boto3
import time
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
# อ้างอิงตาราง
table_data = dynamodb.Table('DisasterRequests')
table_counter = dynamodb.Table('Counters')


def calculate_priority(incident_type, description):
    # กำหนดคะแนนพื้นฐานตามความรุนแรงของประเภทภัยพิบัติ
    base_scores = {
        'สึนามิ': 70,       
        'น้ำท่วม': 60,  
        'ไฟไหม้': 60,
        'พายุ': 50,      
        'ดินถล่ม': 40,    
    }
    
    # เริ่มต้นคะแนนจากประเภทภัย (ถ้าไม่ระบุให้ 20)
    score = base_scores.get(incident_type, 20)

    # จำกัดคะแนนไม่ให้เกิน 100
    return min(score, 100)

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        incident_type = body.get('incident_type', 'General')
        description = body.get('description', 'ไม่มีรายละเอียด')
        latitude = Decimal(str(body.get('latitude', 0.0)))
        longitude = Decimal(str(body.get('longitude', 0.0)))
        priority_score = calculate_priority(incident_type, description)
        
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
            'incident_type': incident_type,
            'description': description,
            'priority_score': Decimal(str(priority_score)),
            'status': 'New',
            'latitude': latitude,
            'longitude': longitude,
            'reported_time': now,
            'last_updated': now
        }
        
        table_data.put_item(Item=item)
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'บันทึกสำเร็จ',
                'request_id': auto_request_id
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        print(e)
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
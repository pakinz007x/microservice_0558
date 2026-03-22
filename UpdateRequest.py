import json
import boto3
from datetime import datetime
from decimal import Decimal

# Helper สำหรับจัดการตัวเลข Decimal ใน JSON
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('DisasterRequests')

def lambda_handler(event, context):
    try:
        # 1. ดึง ID จาก URL Path (เช่น /requests/req_001)
        path_params = event.get('pathParameters')
        req_id = path_params.get('id') if path_params else None
        
        if not req_id:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Missing ID'})}

        # 2. รับข้อมูลที่ต้องการแก้จาก Body
        body = json.loads(event.get('body', '{}'))
        
        # เตรียมคำสั่ง Update แบบ Dynamic (ส่งอะไรมา แก้แค่นั้น)
        update_expr = "SET last_updated = :now"
        attr_names = {}
        attr_values = {':now': datetime.utcnow().isoformat() + 'Z'}
        
        # รายการฟิลด์ที่อนุญาตให้แก้ไข
        fields = ['status', 'incident_type', 'description', 'priority_score', 'latitude', 'longitude']
        
        for f in fields:
            if f in body:
                update_expr += f", #{f} = :{f}"
                attr_names[f"#{f}"] = f
                val = body[f]
                # ถ้าเป็นตัวเลข ต้องแปลงเป็น Decimal ก่อนลง DynamoDB
                if f in ['priority_score', 'latitude', 'longitude']:
                    val = Decimal(str(val))
                attr_values[f":{f}"] = val

        update_params = {
            'Key': {'request_id': req_id},
            'UpdateExpression': update_expr,
            'ExpressionAttributeValues': attr_values,
            'ReturnValues': "ALL_NEW"
        }

        if attr_names:
            update_params['ExpressionAttributeNames'] = attr_names
        # 3. อัปเดตลงฐานข้อมูล
        response = table.update_item(**update_params)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Update Successful',
                'data': response.get('Attributes')
            }, cls=DecimalEncoder, ensure_ascii=False)
        }

    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
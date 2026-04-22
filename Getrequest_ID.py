import json
import boto3
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('DisasterRequests')

def lambda_handler(event, context):
    current_trace_id = context.aws_request_id
    try:
        path_params = event.get('pathParameters')
        req_id = path_params.get('id') if path_params else None
        
        if not req_id:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Missing ID'})}

        # ใช้ Query ผ่าน Index
        response = table.query(
            IndexName='request_id-index', 
            KeyConditionExpression=boto3.dynamodb.conditions.Key('request_id').eq(req_id)
        )
        
        items = response.get('Items', [])
        
        if not items:
            return {'statusCode': 404, 'body': json.dumps({'error': 'Not Found'})}

        # เลือกข้อมูลตัวแรกที่เจอ (เพราะ ID ควรมีตัวเดียว)
        item = items[0]

        # สร้าง Dictionary ใหม่เพื่อเรียงลำดับฟิลด์และเลือกเฉพาะที่ต้องการ
        formatted_item = {
            "request_id": item.get("request_id"),
            "trace_id": item.get("trace_id", "N/A"),
            "incident_type": item.get("incident_type", "ทั่วไป"), # เพิ่มประเภทภัย
            "status": item.get("status"),
            "description": item.get("description"),
            "priority_score": item.get("priority_score"),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "reported_time": item.get("reported_time"),
            "last_updated": item.get("last_updated")
        }

        print(json.dumps({
            "operation": "GET_BY_ID",
            "request_id": req_id,
            "trace_id": current_trace_id,
            "status": "SUCCESS"
        }))

        # ส่งกลับแบบไม่มี indent ใน json.dumps เพื่อให้เป็นบรรทัดเดียว หรือตามมาตรฐาน JSON
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "X-Trace-Id": current_trace_id
            },
            # ส่งแค่ formatted_item ออกไปตรงๆ ใน body
            "body": json.dumps(formatted_item, ensure_ascii=False, cls=DecimalEncoder)
        }

    except Exception as e:
        print(json.dumps({"operation": "GET_BY_ID_ERROR", "trace_id": current_trace_id, "error": str(e)}))
        return {
            'statusCode': 500, 
            'body': json.dumps({'error': str(e), 'trace_id': current_trace_id}, indent=2)
        }
import json
import boto3
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('DisasterRequests')

def lambda_handler(event, context):
    try:
        response = table.scan()
        items = response.get('Items', [])

        # เรียงตาม priority_score มาก -> น้อย
        items.sort(key=lambda x: x.get('request_id'))

        # เลือกเฉพาะ field ที่อ่านง่าย
        simple_items = []
        for item in items:
            simple_items.append({
                "request_id": item.get("request_id"),
                "incident_type": item.get("incident_type", "ทั่วไป"), # เพิ่มประเภทภัย
                "status": item.get("status"),
                "description": item.get("description"),
                "priority_score": item.get("priority_score"),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "reported_time": item.get("reported_time"),
                "last_updated": item.get("last_updated")
            })

        result = {
            "count": len(simple_items),
            "data": simple_items
        }

        print(json.dumps(result, indent=2, ensure_ascii=False, cls=DecimalEncoder))

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(result, ensure_ascii=False, cls=DecimalEncoder)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
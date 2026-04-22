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
    current_trace_id = context.aws_request_id
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
                "trace_id": item.get("trace_id", "N/A"),
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
            "data": simple_items,
            "fetched_by_trace_id": current_trace_id
        }

        print(json.dumps({
            "operation": "GET_ALL_REQUESTS",
            "count": len(simple_items),
            "trace_id": current_trace_id
        }))

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "X-Trace-Id": current_trace_id
            },
            "body": json.dumps(result, indent=2, ensure_ascii=False, cls=DecimalEncoder)
        }

    except Exception as e:
        print(json.dumps({"operation": "GET_ERROR", "trace_id": current_trace_id, "error": str(e)}))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e), "trace_id": current_trace_id})
        }
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
        # ดึงข้อมูลทั้งหมดจากตาราง
        response = table.scan()
        items = response.get('Items', [])

        # 1. เรียงลำดับตาม priority_score จากมากไปน้อย (เพื่อให้เคสด่วนอยู่บนสุด)
        items.sort(key=lambda x: x.get('priority_score', 0), reverse=True)

        # 2. ปรับโครงสร้างข้อมูลที่ส่งกลับ (ตัด water_level, เพิ่ม incident_type)
        simple_items = []
        for item in items:
            simple_items.append({
                "request_id": item.get("request_id"),
                "incident_type": item.get("incident_type", "ทั่วไป"), # เพิ่มฟิลด์ใหม่
                "status": item.get("status"),
                "description": item.get("description"),
                # "water_level": item.get("water_level"),  # <-- ลบออกแล้ว
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

        # พิมพ์ Log เพื่อตรวจสอบภาษาไทยใน CloudWatch
        print(json.dumps(result, indent=2, ensure_ascii=False, cls=DecimalEncoder))

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(result, ensure_ascii=False, cls=DecimalEncoder, indent=4)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}, ensure_ascii=False)
        }
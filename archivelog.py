import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')
BUCKET_NAME = 'disaster-archive-log' # <--- แก้ตรงนี้

def lambda_handler(event, context):
    try:
        for record in event['Records']:
            # ตรวจจับเฉพาะเหตุการณ์ "REMOVE" (การลบข้อมูล)
            if record['eventName'] == 'REMOVE':
                # ดึงข้อมูลเก่า (ก่อนถูกลบ) ออกมา
                # ข้อมูลใน Stream จะมาในรูปแบบ DynamoDB JSON (มีชนิดข้อมูลติดมาด้วย)
                raw_data = record['dynamodb']['OldImage']
                
                # แปลง DynamoDB JSON ให้เป็น JSON ปกติที่อ่านง่าย
                # ตัวอย่าง: {"request_id": {"S": "req_001"}} -> {"request_id": "req_001"}
                clean_data = {}
                for key, value in raw_data.items():
                    clean_data[key] = list(value.values())[0]

                # ตั้งชื่อไฟล์: archived/ปี-เดือน-วัน/ID_เวลา.json
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_name = f"archived/{clean_data['request_id']}_{timestamp}.json"

                # อัปโหลดขึ้น S3
                s3.put_object(
                    Bucket=BUCKET_NAME,
                    Key=file_name,
                    Body=json.dumps(clean_data, indent=4, ensure_ascii=False),
                    ContentType='application/json'
                )
                print(f"Successfully archived: {file_name}")

        return {'status': 'success'}
    except Exception as e:
        print(f"Error: {str(e)}")
        return {'status': 'error', 'message': str(e)}
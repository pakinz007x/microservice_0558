import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')
BUCKET_NAME = 'disaster-archive-log' # <--- ตรวจสอบชื่อ Bucket ให้ถูกต้องนะครับ

def lambda_handler(event, context):
    # ID สำหรับการทำงานของ Lambda ตัวนี้เอง (เพื่อ Observability)
    archive_event_id = context.aws_request_id
    
    try:
        for record in event['Records']:
            # ตรวจจับเฉพาะเหตุการณ์ "REMOVE" (ข้อมูลถูกลบจาก DynamoDB)
            if record['eventName'] == 'REMOVE':
                # 1. ดึงข้อมูลเก่า (OldImage)
                raw_data = record['dynamodb']['OldImage']
                
                # 2. แปลง DynamoDB JSON เป็น JSON ปกติ
                clean_data = {}
                for key, value in raw_data.items():
                    # ดึงค่าแรกใน dict (เช่น {"S": "val"} -> "val")
                    clean_data[key] = list(value.values())[0]

                # 3. จัดการเรื่อง Trace ID
                # ดึง Trace ID เดิมที่เคยเก็บไว้ตอน Submit/Update มาใส่ในไฟล์ Backup
                original_trace_id = clean_data.get('trace_id', 'N/A')
                
                # เพิ่มข้อมูลการ Archive ลงในไฟล์
                clean_data['archive_metadata'] = {
                    'archived_at': datetime.utcnow().isoformat() + 'Z',
                    'archive_lambda_trace_id': archive_event_id,
                    'original_trace_id': original_trace_id
                }

                # 4. ตั้งชื่อไฟล์: archived/ID_Timestamp.json
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_name = f"archived/{clean_data['request_id']}_{timestamp}.json"

                # 5. อัปโหลดขึ้น S3
                s3.put_object(
                    Bucket=BUCKET_NAME,
                    Key=file_name,
                    Body=json.dumps(clean_data, indent=4, ensure_ascii=False),
                    ContentType='application/json'
                )
                
                # Structured Logging เพื่อให้ตามรอยจาก CloudWatch ได้
                print(json.dumps({
                    "operation": "ARCHIVE_TO_S3",
                    "request_id": clean_data.get('request_id'),
                    "original_trace_id": original_trace_id,
                    "archive_trace_id": archive_event_id,
                    "file_path": file_name,
                    "status": "SUCCESS"
                }))

        return {'status': 'success', 'archive_event_id': archive_event_id}
        
    except Exception as e:
        error_msg = f"Error during archive: {str(e)}"
        print(json.dumps({
            "operation": "ARCHIVE_ERROR",
            "archive_event_id": archive_event_id,
            "error": str(e)
        }))
        return {'status': 'error', 'message': error_msg}
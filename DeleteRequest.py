import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('DisasterRequests')

def lambda_handler(event, context):
    current_trace_id = context.aws_request_id
    try:
        # 1. รับ ID จาก Path Parameters (เช่น /requests/{id})
        path_params = event.get('pathParameters')
        req_id = path_params.get('id') if path_params else None
        
        if not req_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'ต้องระบุ request_id ที่ต้องการลบ',
                    'trace_id': current_trace_id
                }, ensure_ascii=False, indent=2)
            }

        # 2. สั่งลบข้อมูลใน DynamoDB
        # เมื่อคำสั่งนี้สำเร็จ Stream จะทำงานทันที (Async Archive เริ่มทำงาน)
        table.delete_item(
            Key={'request_id': req_id}
        )

        print(json.dumps({
            "operation": "DELETE_REQUEST",
            "target_request_id": req_id,
            "trace_id": current_trace_id,
            "status": "SUCCESS",
            "note": "Async archiving triggered via DynamoDB Streams"
        }))

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': f'ลบข้อมูล {req_id} สำเร็จแล้ว และระบบกำลังสำรองข้อมูลลง S3',
                'trace_id': current_trace_id,
                'target_id': req_id
            }, ensure_ascii=False)
        }

    except Exception as e:
        print(json.dumps({
            "operation": "DELETE_ERROR",
            "trace_id": current_trace_id,
            "error": str(e)
        }))
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'trace_id': current_trace_id
            }, ensure_ascii=False, indent=2)
        }
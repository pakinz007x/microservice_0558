import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table_requests = dynamodb.Table('DisasterRequests')
table_friend = dynamodb.Table('SerevityData')

def calculate_keyword_score(description):
    # กำหนดคะแนนฐาน
    score = 20 
    # ทำความสะอาดข้อความเบื้องต้น (เอาช่องว่างออก)
    text = description.replace(" ", "")

    # กลุ่มคำและคะแนน (รวมคำที่มีความหมายคล้ายกัน)
    keyword_groups = {
        # กลุ่มวิกฤตสูงสุด (ต้องการความช่วยเหลือทันที)
        90: ["เสียชีวิต", "ตาย", "ศพ", "ร่างผู้เสียชีวิต", "ไม่หายใจ", "จมน้ำ"],
        
        # กลุ่มความเสียหายรุนแรงต่อโครงสร้างและชีวิต
        70: ["ถล่ม", "พัง", "ทรุด", "ระเบิด", "ตึกถล่ม", "อาคารพัง", "ไหม้หนัก", "สูง"],
        
        # กลุ่มติดค้างและอันตรายสูง
        60: ["ติดข้างใน", "ติดใน", "ออกมาไม่ได้", "ติดอยู่", "ติดใต้ซาก", "หนีไม่ได้"],
        
        # กลุ่มการบาดเจ็บและเลือด
        50: ["บาดเจ็บ", "เจ็บ", "เลือด", "แผล", "สาหัส", "หมดสติ", "ปั๊มหัวใจ", "กู้ชีพ"],
        
        # กลุ่มผู้เปราะบาง (อันนี้ควรมีมาก!)
        40: ["เด็ก", "คนชรา", "คนแก่", "ผู้ป่วยติดเตียง", "คนพิการ", "ทารก", "สูงอายุ"],
        
        # กลุ่มเหตุการณ์และคำร้องขอ
        30: ["วิกฤต", "ฉุกเฉิน", "ด่วน", "ช่วยเหลือด้วย", "ช่วยด้วย", "ไฟไหม้", "น้ำท่วมสูง"],
        
        # กลุ่มสถานการณ์ทั่วไป
        20: ["ควัน", "กลิ่นไหม้", "ฝนตกหนัก", "ระดับน้ำเพิ่ม", "ขอความช่วยเหลือ"]
}

    found_scores = []
    for points, words in keyword_groups.items():
        if any(word in text for word in words):
            found_scores.append(points)
    
    # ถ้าเจอหลายกลุ่ม ให้เอาคะแนนสะสมกัน หรือเลือกค่าสูงสุด + โบนัส
    if found_scores:
        # วิธีแบบสะสม: เอาค่าสูงสุด + (จำนวนกลุ่มที่เจอเพิ่มเติม * 10)
        final_keyword_score = max(found_scores) + (len(found_scores) - 1) * 10
        return min(final_keyword_score, 100) # ไม่ให้เกิน 100
    
    return score

def lambda_handler(event, context):
    trace_id = context.aws_request_id
    urgency_map = {"critical": 100, "high": 70, "medium": 40, "low": 20}
    priority_group_map = {"P1": 100, "P2": 60, "P3": 30}

    for record in event['Records']:
        if record['eventName'] in ['INSERT', 'MODIFY']:
            new_image = record['dynamodb']['NewImage']
            
            # ดึงค่าเดิม
            req_id = new_image['request_id']['S']
            description = new_image['description']['S']
            target_incident_id = new_image.get('incident_Id', {}).get('S', 'N/A')

            # --- ส่วนที่ 1: ดึงข้อมูลเพื่อน ---
            friend_score_avg = 50
            if target_incident_id != 'N/A':
                try:
                    res = table_friend.get_item(Key={'incident_Id': target_incident_id})
                    if 'Item' in res:
                        f_item = res['Item']
                        u_score = urgency_map.get(f_item.get('urgencyLevel'), 40)
                        p_score = priority_group_map.get(f_item.get('priorityGroup'), 30)
                        friend_score_avg = (u_score + p_score) / 2
                except:
                    pass

            # --- ส่วนที่ 2: คำนวณ Keyword Score แบบยืดหยุ่น ---
            keyword_score = calculate_keyword_score(description)

            # --- ส่วนที่ 3: รวมคะแนน ---
            # น้ำหนัก: Keyword เรา 60% + ข้อมูลเพื่อน 40% (ปรับเปลี่ยนได้ตามความเหมาะสม)
            final_priority = (keyword_score * 0.7) + (friend_score_avg * 0.3)

            # 5. อัปเดตกลับ
            table_requests.update_item(
                Key={'request_id': req_id},
                UpdateExpression="SET priority_score = :p, #stat = :s, processed_by = :t",
                ExpressionAttributeNames={
                    '#stat': 'status'  # บอก DynamoDB ว่า #stat คือฟิลด์ชื่อ status นะ
                },
                ExpressionAttributeValues={
                    ':p': Decimal(str(round(final_priority, 2))),
                    ':s': 'PROCESSED',
                    ':t': trace_id
                }
            )

            print(f"Processed {req_id}: Keyword={keyword_score}, Friend={friend_score_avg}, Final={final_priority}")

    return {'status': 'success'}
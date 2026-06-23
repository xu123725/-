import sys
import os
import json
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import Question

def fix_question_types():
    db: Session = SessionLocal()
    try:
        print("开始扫描题库...")
        # 查找所有的单选题
        questions = db.query(Question).filter(Question.question_type == 'single').all()
        print(f"找到 {len(questions)} 道被标记为单选题的题目，开始检查...")
        
        fixed_multiple = 0
        fixed_true_false = 0
        
        for q in questions:
            try:
                options = json.loads(q.options_json)
                answer = str(q.answer).strip()
                
                # 检查判断题
                if len(options) == 2:
                    opt_str = "".join(options)
                    if any(k in opt_str for k in ["正确", "错误", "对", "错", "是", "否"]):
                        q.question_type = 'true_false'
                        fixed_true_false += 1
                        continue
                
                # 检查多选题：选项超过2个，且答案长度大于1（排除例如 "A" 这种，多选通常是 "ABC"）
                # 为了防止带空格，可以把空格去掉
                answer_clean = answer.replace(" ", "").replace(",", "")
                if len(options) > 2 and len(answer_clean) > 1:
                    q.question_type = 'multiple'
                    fixed_multiple += 1
                    continue
                    
            except Exception as e:
                print(f"解析题目 {q.id} 时出错: {e}")
                continue
                
        if fixed_multiple > 0 or fixed_true_false > 0:
            db.commit()
            print(f"✅ 修复完成！已将 {fixed_multiple} 道题修正为多选题，{fixed_true_false} 道题修正为判断题。")
        else:
            print("✨ 没有发现需要修复的单选题。")
            
    except Exception as e:
        print(f"❌ 执行出错: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_question_types()

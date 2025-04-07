from datetime import datetime

from models import db, Machine


def insert_sample_machines():
    sample_machines = []
    for i in range(22,1000):
        product_id = "p100"+str(i)
        step_id = "step1"+str(i)
        x=  {
            "machine_id": product_id+step_id,
            "product_id": product_id,
            "step_id": step_id,
            "recipe_id": "R001",
            "review_id": "RV001",
            "review_tool": "SEM-Review",
            "inspection_tool": "AOI-X200",
            "sample_wafers": "1,3,5,7,9",
            "machine_type": "SEM",

        }
        sample_machines.append(x)


    # 确保在应用上下文中执行
    from app import app  # 替换为你的应用模块
    with app.app_context():
        for data in sample_machines:
            machine = Machine(
                machine_id=data["machine_id"],
                product_id=data["product_id"],
                step_id=data["step_id"],
                recipe_id=data["recipe_id"],
                review_id=data["review_id"],
                review_tool=data["review_tool"],
                inspection_tool=data["inspection_tool"],
                sample_wafers=data["sample_wafers"],
                machine_type=data["machine_type"],

                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(machine)

        try:
            db.session.commit()
            print(f"成功插入{len(sample_machines)}条机台数据")
        except Exception as e:
            db.session.rollback()
            print(f"插入数据时出错: {e}")


if __name__ == "__main__":
    insert_sample_machines()

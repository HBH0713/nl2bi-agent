"""生成 5 万行级别的电商测试数据"""
import random
import asyncio
import os
from datetime import date, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

REGIONS = ["华东", "华南", "华北", "西南", "西北", "东北"]
PROVINCES = ["浙江", "广东", "北京", "四川", "陕西", "辽宁", "上海", "江苏", "湖北", "福建"]
CHANNELS = ["官网", "APP", "小程序", "地推", "合作伙伴"]
STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled", "returned"]
CATEGORIES = ["电子产品", "家居用品", "服装鞋帽", "食品饮料", "美妆个护"]
STATUS_WEIGHTS = [0.05, 0.15, 0.20, 0.45, 0.10, 0.05]

PRODUCT_NAMES = {
    "电子产品": ["无线蓝牙耳机", "智能手表", "平板电脑", "手机壳", "充电宝", "USB数据线", "机械键盘", "显示器支架"],
    "家居用品": ["记忆棉枕头", "遮光窗帘", "不锈钢锅具", "收纳盒套装", "LED台灯", "地毯", "晾衣架", "浴室防滑垫"],
    "服装鞋帽": ["运动T恤", "休闲牛仔裤", "跑步鞋", "防晒帽", "羽绒服", "商务衬衫", "帆布包", "羊毛围巾"],
    "食品饮料": ["有机绿茶", "坚果礼盒", "即溶咖啡", "红枣枸杞茶", "进口巧克力", "橄榄油", "蜂蜜", "杂粮粥料"],
    "美妆个护": ["保湿面霜", "防晒喷雾", "洗面奶", "口红", "护手霜", "洗发水", "沐浴露", "面膜套装"],
}

CUSTOMER_NAMES = ["张三", "李四", "王五", "赵六", "陈七", "周八", "吴九", "郑十",
                  "刘明", "黄丽", "孙伟", "马芳", "朱强", "胡静", "林涛", "何雪"]


def generate_products(n=200):
    products = []
    for i in range(1, n + 1):
        cat = random.choice(CATEGORIES)
        name = random.choice(PRODUCT_NAMES[cat]) + f" {random.choice(['Pro','Plus','Max','Lite',''])}{random.randint(1,99)}"
        cost = round(random.uniform(10, 500), 2)
        products.append({
            "product_name": name.strip(),
            "category": cat,
            "unit_price": round(cost * random.uniform(1.3, 2.5), 2),
            "cost_price": cost,
            "supplier": random.choice(["深圳科技", "广州制造", "义乌商贸", "北京优选", "上海品质"]),
        })
    return products


async def seed(conn_str: str, num_orders: int = 50000):
    engine = create_async_engine(conn_str)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM products"))
        if result.scalar() > 0:
            print("Database already has data, skipping seed.")
            return

        products = generate_products(200)
        for p in products:
            await session.execute(
                text("INSERT INTO products (product_name, category, unit_price, cost_price, supplier) VALUES (:product_name, :category, :unit_price, :cost_price, :supplier)"),
                p
            )
        await session.flush()
        print(f"Inserted {len(products)} products")

        customers = []
        for i in range(1, 5001):
            customers.append({
                "name": random.choice(CUSTOMER_NAMES) + str(random.randint(1, 9999)),
                "region": random.choice(REGIONS),
                "province": random.choice(PROVINCES),
                "city": random.choice(["杭州", "广州", "北京", "成都", "西安", "沈阳", "上海", "武汉", "深圳", "南京"]),
                "channel": random.choice(CHANNELS),
                "created_at": date(2024, 1, 1) + timedelta(days=random.randint(0, 700)),
            })

        for c in customers:
            await session.execute(
                text("INSERT INTO customers (name, region, province, city, channel, created_at) VALUES (:name, :region, :province, :city, :channel, :created_at)"),
                c
            )
        await session.flush()
        print(f"Inserted {len(customers)} customers")

        batch_size = 1000
        for batch_start in range(0, num_orders, batch_size):
            batch_end = min(batch_start + batch_size, num_orders)
            for _ in range(batch_start, batch_end):
                customer_id = random.randint(1, 5000)
                region = random.choice(REGIONS)
                order_date = date(2025, 1, 1) + timedelta(days=random.randint(0, 500))
                status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
                channel = random.choice(CHANNELS)
                num_items = random.randint(1, 5)

                total = 0.0
                items = []
                for _ in range(num_items):
                    product_id = random.randint(1, 200)
                    qty = random.randint(1, 10)
                    result = await session.execute(
                        text("SELECT unit_price FROM products WHERE product_id = :pid"),
                        {"pid": product_id}
                    )
                    row = result.fetchone()
                    if row is None:
                        continue
                    unit_price = float(row[0])
                    subtotal = round(qty * unit_price, 2)
                    total += subtotal
                    items.append({"product_id": product_id, "quantity": qty, "unit_price": unit_price})

                if not items:
                    continue

                discount = round(random.uniform(0, total * 0.1), 2)
                total_after_discount = round(total - discount, 2)

                result = await session.execute(
                    text("""INSERT INTO orders (customer_id, order_date, status, total_amount, discount_amount, region, channel)
                            VALUES (:cid, :od, :st, :ta, :da, :r, :ch) RETURNING order_id"""),
                    {"cid": customer_id, "od": order_date, "st": status, "ta": total_after_discount, "da": discount, "r": region, "ch": channel}
                )
                order_id = result.scalar()

                for item in items:
                    await session.execute(
                        text("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (:oid, :pid, :qty, :up)"),
                        {"oid": order_id, "pid": item["product_id"], "qty": item["quantity"], "up": item["unit_price"]}
                    )

            await session.flush()
            print(f"Inserted orders {batch_start+1}-{batch_end}/{num_orders}")

        result = await session.execute(text("SELECT order_id, total_amount FROM orders WHERE status IN ('returned','cancelled') ORDER BY RANDOM() LIMIT :n"), {"n": int(num_orders * 0.03)})
        refund_count = 0
        for row in result.fetchall():
            order_id, total = int(row[0]), float(row[1])
            await session.execute(
                text("INSERT INTO refunds (order_id, refund_amount, refund_reason, refund_date) VALUES (:oid, :amt, :reason, :rd)"),
                {"oid": order_id, "amt": round(total * random.uniform(0.5, 1.0), 2),
                 "reason": random.choice(["质量问题", "不喜欢", "发货延迟", "商品与描述不符", "重复下单"]),
                 "rd": date(2025, 1, 1) + timedelta(days=random.randint(0, 510))}
            )
            refund_count += 1
        print(f"Inserted {refund_count} refunds")

        await session.commit()

    await engine.dispose()
    print("Seed complete!")


async def main():
    pg_host = os.getenv("PG_HOST", "localhost")
    pg_port = os.getenv("PG_PORT", "5432")
    pg_db = os.getenv("PG_DATABASE", "bi_demo")
    pg_user = os.getenv("PG_USER", "bi_agent")
    pg_pass = os.getenv("PG_PASSWORD", "changeme")
    conn_str = f"postgresql+asyncpg://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
    await seed(conn_str, num_orders=50000)

if __name__ == "__main__":
    asyncio.run(main())

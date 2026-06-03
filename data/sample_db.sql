-- 电商 BI 示例数据库：5 张表，模拟真实业务场景

CREATE EXTENSION IF NOT EXISTS vector;

-- 用户只读角色（安全硬兜底）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'bi_readonly') THEN
        CREATE ROLE bi_readonly WITH LOGIN PASSWORD 'readonly123' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END $$;

-- 1. 客户表
CREATE TABLE IF NOT EXISTS customers (
    customer_id   SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    region        VARCHAR(20)  NOT NULL CHECK (region IN ('华东','华南','华北','西南','西北','东北')),
    province      VARCHAR(50),
    city          VARCHAR(50),
    channel       VARCHAR(20)  CHECK (channel IN ('官网','APP','小程序','地推','合作伙伴')),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE customers IS '客户信息表：存储所有注册客户的基本信息，包括所属区域、获客渠道';
COMMENT ON COLUMN customers.customer_id IS '客户唯一标识';
COMMENT ON COLUMN customers.region IS '所属大区：华东/华南/华北/西南/西北/东北';
COMMENT ON COLUMN customers.channel IS '获客渠道：官网/APP/小程序/地推/合作伙伴';

-- 2. 产品表
CREATE TABLE IF NOT EXISTS products (
    product_id    SERIAL PRIMARY KEY,
    product_name  VARCHAR(200) NOT NULL,
    category      VARCHAR(50)  NOT NULL CHECK (category IN ('电子产品','家居用品','服装鞋帽','食品饮料','美妆个护')),
    unit_price    DECIMAL(10, 2) NOT NULL CHECK (unit_price > 0),
    cost_price    DECIMAL(10, 2) NOT NULL CHECK (cost_price > 0),
    supplier      VARCHAR(100),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE products IS '产品信息表：存储所有在售产品的信息';
COMMENT ON COLUMN products.unit_price IS '销售单价（元）';
COMMENT ON COLUMN products.cost_price IS '成本单价（元）';
COMMENT ON COLUMN products.category IS '产品类目';

-- 3. 订单表
CREATE TABLE IF NOT EXISTS orders (
    order_id      SERIAL PRIMARY KEY,
    customer_id   INT NOT NULL REFERENCES customers(customer_id),
    order_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    status        VARCHAR(20) NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','confirmed','shipped','delivered','cancelled','returned')),
    total_amount  DECIMAL(12, 2) NOT NULL CHECK (total_amount >= 0),
    discount_amount DECIMAL(12, 2) DEFAULT 0 CHECK (discount_amount >= 0),
    region        VARCHAR(20) NOT NULL,
    channel       VARCHAR(20)
);
COMMENT ON TABLE orders IS '订单主表：存储每笔订单的汇总信息';
COMMENT ON COLUMN orders.order_id IS '订单唯一标识';
COMMENT ON COLUMN orders.total_amount IS '订单总金额（元），已扣除折扣';
COMMENT ON COLUMN orders.status IS '订单状态：pending待支付/confirmed已确认/shipped已发货/delivered已签收/cancelled已取消/returned已退货';
COMMENT ON COLUMN orders.order_date IS '下单日期';

-- 4. 订单明细表
CREATE TABLE IF NOT EXISTS order_items (
    item_id       SERIAL PRIMARY KEY,
    order_id      INT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id    INT NOT NULL REFERENCES products(product_id),
    quantity      INT NOT NULL CHECK (quantity > 0),
    unit_price    DECIMAL(10, 2) NOT NULL CHECK (unit_price >= 0),
    subtotal      DECIMAL(12, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);
COMMENT ON TABLE order_items IS '订单明细表：每笔订单中每个产品的购买明细';
COMMENT ON COLUMN order_items.quantity IS '购买数量';
COMMENT ON COLUMN order_items.subtotal IS '小计 = 数量 × 单价（自动计算）';

-- 5. 退款表
CREATE TABLE IF NOT EXISTS refunds (
    refund_id     SERIAL PRIMARY KEY,
    order_id      INT NOT NULL REFERENCES orders(order_id),
    refund_amount DECIMAL(12, 2) NOT NULL CHECK (refund_amount > 0),
    refund_reason VARCHAR(200),
    refund_date   DATE NOT NULL DEFAULT CURRENT_DATE
);
COMMENT ON TABLE refunds IS '退款记录表：存储所有退款申请和完成记录';
COMMENT ON COLUMN refunds.refund_amount IS '退款金额（元）';

-- 索引
CREATE INDEX IF NOT EXISTS idx_orders_date       ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_region      ON orders(region);
CREATE INDEX IF NOT EXISTS idx_orders_status      ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_customer    ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order  ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_customers_region   ON customers(region);
CREATE INDEX IF NOT EXISTS idx_products_category  ON products(category);

-- 只读权限
GRANT CONNECT ON DATABASE bi_demo TO bi_readonly;
GRANT USAGE ON SCHEMA public TO bi_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO bi_readonly;

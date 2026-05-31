-- ============================================================
-- АНАЛИЗ ПОЛЬЗОВАТЕЛЬСКОЙ ВОРОНКИ ИНТЕРНЕТ-МАГАЗИНА
-- ============================================================

-- 1. Количество пользователей на каждом этапе воронки
WITH funnel AS (
    SELECT
        event_type,
        COUNT(DISTINCT user_id) AS users_count,
        ROUND(COUNT(DISTINCT user_id) * 100.0 / 
              MAX(COUNT(DISTINCT user_id)) OVER (), 2) AS pct_from_top
    FROM events
    GROUP BY event_type
),
ordered_funnel AS (
    SELECT *,
        CASE event_type
            WHEN 'view_product'    THEN 1
            WHEN 'add_to_cart'     THEN 2
            WHEN 'begin_checkout'  THEN 3
            WHEN 'enter_payment'   THEN 4
            WHEN 'purchase'        THEN 5
        END AS step_order
    FROM funnel
)
SELECT
    step_order,
    event_type,
    users_count,
    pct_from_top AS pct_of_top_step,
    ROUND(users_count * 100.0 / LAG(users_count) OVER (ORDER BY step_order), 2) AS step_conversion_pct
FROM ordered_funnel
ORDER BY step_order;


-- 2. Конверсия по устройствам
SELECT
    device,
    COUNT(DISTINCT user_id) AS total_users,
    COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS buyers,
    ROUND(
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) * 100.0
        / COUNT(DISTINCT user_id), 2
    ) AS purchase_conversion_pct
FROM events
GROUP BY device
ORDER BY purchase_conversion_pct DESC;


-- 3. DAU — ежедневная активная аудитория
SELECT
    DATE(event_time) AS event_date,
    COUNT(DISTINCT user_id) AS dau
FROM events
WHERE event_type = 'view_product'
GROUP BY DATE(event_time)
ORDER BY event_date;


-- 4. Конверсия по категориям товаров
SELECT
    category,
    COUNT(DISTINCT user_id)                                                        AS viewers,
    COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END)             AS buyers,
    ROUND(
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) * 100.0
        / COUNT(DISTINCT user_id), 2
    )                                                                              AS conversion_pct,
    ROUND(AVG(CASE WHEN event_type = 'purchase' THEN item_price END), 2)           AS avg_order_value
FROM events
GROUP BY category
ORDER BY conversion_pct DESC;


-- 5. Dropout rate — доля пользователей, ушедших на каждом этапе
WITH user_max_step AS (
    SELECT
        user_id,
        MAX(CASE event_type
            WHEN 'view_product'    THEN 1
            WHEN 'add_to_cart'     THEN 2
            WHEN 'begin_checkout'  THEN 3
            WHEN 'enter_payment'   THEN 4
            WHEN 'purchase'        THEN 5
        END) AS last_step
    FROM events
    GROUP BY user_id
)
SELECT
    last_step,
    CASE last_step
        WHEN 1 THEN 'view_product'
        WHEN 2 THEN 'add_to_cart'
        WHEN 3 THEN 'begin_checkout'
        WHEN 4 THEN 'enter_payment'
        WHEN 5 THEN 'purchase'
    END AS dropout_at_step,
    COUNT(*) AS users_dropped,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_all_users
FROM user_max_step
GROUP BY last_step
ORDER BY last_step;

INSERT INTO sectors (slug, name_ko, name_en, description, sort_order)
VALUES
  ('semiconductor', '반도체', 'Semiconductor', '반도체, 메모리, 장비, 스토리지, AI 반도체 섹터', 10)
ON CONFLICT (slug) DO UPDATE SET
  name_ko = EXCLUDED.name_ko,
  name_en = EXCLUDED.name_en,
  description = EXCLUDED.description,
  sort_order = EXCLUDED.sort_order,
  active = TRUE,
  updated_at = now();

INSERT INTO themes (slug, name_ko, name_en, description, sort_order)
VALUES
  ('hbm-memory', 'HBM/메모리', 'HBM / Memory', 'HBM, DRAM, NAND, 메모리 사이클', 10),
  ('ai-accelerators', 'AI 가속기', 'AI Accelerators', 'GPU, AI ASIC, 가속기 생태계', 20),
  ('semicap-equipment', '반도체 장비', 'Semicap Equipment', '전공정/후공정 반도체 장비', 30),
  ('storage', '스토리지', 'Storage', 'HDD, SSD, NAND 스토리지', 40)
ON CONFLICT (slug) DO UPDATE SET
  name_ko = EXCLUDED.name_ko,
  name_en = EXCLUDED.name_en,
  description = EXCLUDED.description,
  sort_order = EXCLUDED.sort_order,
  active = TRUE,
  updated_at = now();

INSERT INTO watchlists (slug, name_ko, name_en, description, parent_type, parent_slug, sort_order)
VALUES
  ('semiconductor-core', '반도체 핵심 Watchlist', 'Semiconductor Core Watchlist', '기존 반도체/메모리/장비/AI 반도체 17종목 watchlist', 'sector', 'semiconductor', 10)
ON CONFLICT (slug) DO UPDATE SET
  name_ko = EXCLUDED.name_ko,
  name_en = EXCLUDED.name_en,
  description = EXCLUDED.description,
  parent_type = EXCLUDED.parent_type,
  parent_slug = EXCLUDED.parent_slug,
  sort_order = EXCLUDED.sort_order,
  active = TRUE,
  updated_at = now();

INSERT INTO assets (symbol, display_name_ko, display_name_en, asset_type, exchange, currency, country)
VALUES
  ('SNDK', '샌디스크', 'SanDisk', 'stock', 'NASDAQ', 'USD', 'US'),
  ('005930.KS', '삼성전자', 'Samsung Electronics', 'stock', 'KRX', 'KRW', 'KR'),
  ('000660.KS', 'SK하이닉스', 'SK hynix', 'stock', 'KRX', 'KRW', 'KR'),
  ('MU', '마이크론', 'Micron Technology', 'stock', 'NASDAQ', 'USD', 'US'),
  ('STX', '씨게이트', 'Seagate Technology', 'stock', 'NASDAQ', 'USD', 'US'),
  ('WDC', '웨스턴디지털', 'Western Digital', 'stock', 'NASDAQ', 'USD', 'US'),
  ('MRVL', '마벨', 'Marvell Technology', 'stock', 'NASDAQ', 'USD', 'US'),
  ('042700.KQ', '한미반도체', 'Hanmi Semiconductor', 'stock', 'KOSDAQ', 'KRW', 'KR'),
  ('AMAT', '어플라이드 머티어리얼즈', 'Applied Materials', 'stock', 'NASDAQ', 'USD', 'US'),
  ('LRCX', '램리서치', 'Lam Research', 'stock', 'NASDAQ', 'USD', 'US'),
  ('ASML', 'ASML 홀딩', 'ASML Holding', 'stock', 'NASDAQ', 'USD', 'NL'),
  ('080220.KQ', '제주반도체', 'Jeju Semiconductor', 'stock', 'KOSDAQ', 'KRW', 'KR'),
  ('TSM', 'TSMC', 'Taiwan Semiconductor Manufacturing', 'stock', 'NYSE', 'USD', 'TW'),
  ('NVDA', '엔비디아', 'NVIDIA', 'stock', 'NASDAQ', 'USD', 'US'),
  ('AVGO', '브로드컴', 'Broadcom', 'stock', 'NASDAQ', 'USD', 'US'),
  ('AMD', 'AMD', 'Advanced Micro Devices', 'stock', 'NASDAQ', 'USD', 'US'),
  ('INTC', '인텔', 'Intel', 'stock', 'NASDAQ', 'USD', 'US')
ON CONFLICT (symbol) DO UPDATE SET
  display_name_ko = EXCLUDED.display_name_ko,
  display_name_en = EXCLUDED.display_name_en,
  asset_type = EXCLUDED.asset_type,
  exchange = EXCLUDED.exchange,
  currency = EXCLUDED.currency,
  country = EXCLUDED.country,
  active = TRUE,
  updated_at = now();

INSERT INTO asset_sector_map (asset_id, sector_id, is_primary)
SELECT a.asset_id, s.sector_id, TRUE
FROM assets a CROSS JOIN sectors s
WHERE s.slug = 'semiconductor'
  AND a.symbol IN ('SNDK','005930.KS','000660.KS','MU','STX','WDC','MRVL','042700.KQ','AMAT','LRCX','ASML','080220.KQ','TSM','NVDA','AVGO','AMD','INTC')
ON CONFLICT (asset_id, sector_id) DO UPDATE SET is_primary = EXCLUDED.is_primary;

INSERT INTO watchlist_members (watchlist_id, asset_id, sort_order)
SELECT w.watchlist_id, a.asset_id,
       CASE a.symbol
         WHEN 'SNDK' THEN 10 WHEN '005930.KS' THEN 20 WHEN '000660.KS' THEN 30 WHEN 'MU' THEN 40
         WHEN 'STX' THEN 50 WHEN 'WDC' THEN 60 WHEN 'MRVL' THEN 70 WHEN '042700.KQ' THEN 80
         WHEN 'AMAT' THEN 90 WHEN 'LRCX' THEN 100 WHEN 'ASML' THEN 110 WHEN '080220.KQ' THEN 120
         WHEN 'TSM' THEN 130 WHEN 'NVDA' THEN 140 WHEN 'AVGO' THEN 150 WHEN 'AMD' THEN 160 WHEN 'INTC' THEN 170
         ELSE 999
       END AS sort_order
FROM watchlists w CROSS JOIN assets a
WHERE w.slug = 'semiconductor-core'
  AND a.symbol IN ('SNDK','005930.KS','000660.KS','MU','STX','WDC','MRVL','042700.KQ','AMAT','LRCX','ASML','080220.KQ','TSM','NVDA','AVGO','AMD','INTC')
ON CONFLICT (watchlist_id, asset_id) DO UPDATE SET sort_order = EXCLUDED.sort_order;

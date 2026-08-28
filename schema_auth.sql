-- ================================================================
--  구글 로그인 붙이기 - 추가분
--
--  schema.sql 을 다시 돌리지 마세요. 표를 지우고 새로 만듭니다.
--  이 파일만 Supabase SQL Editor 에 붙여넣고 Run 하세요.
--  이미 있는 데이터는 그대로 남습니다.
-- ================================================================


-- ----------------------------------------------------------------
--  1. 누가 넣었는지 적을 칸
--
--     로그인 안 하고 넣은 예약은 null 로 남습니다.
--     기존 예약이 다 그렇게 되며, 예전처럼 모두에게 보입니다.
-- ----------------------------------------------------------------
alter table booking add column if not exists user_id uuid references auth.users(id);

create index if not exists booking_user_idx on booking (user_id, created_at desc);


-- ----------------------------------------------------------------
--  2. 접근 규칙을 다시 씁니다
--
--     로그인한 사람은 자기 것만 보고 고칩니다.
--     로그인 안 한 익명 예약(user_id 가 null)은 예전처럼 누구나 봅니다.
--
--     주의 - 익명 예약이 공개인 것은 로그인 없는 실습을 살려 두려는 것입니다.
--     실제 서비스라면 아래 null 허용을 빼고 로그인을 필수로 만드세요.
-- ----------------------------------------------------------------
drop policy if exists "접수 읽기"   on booking;
drop policy if exists "접수 넣기"   on booking;
drop policy if exists "접수 고치기" on booking;

create policy "접수 읽기" on booking
  for select
  using ( user_id is null or user_id = auth.uid() );

create policy "접수 넣기" on booking
  for insert
  with check ( user_id is null or user_id = auth.uid() );

create policy "접수 고치기" on booking
  for update
  using      ( user_id is null or user_id = auth.uid() )
  with check ( user_id is null or user_id = auth.uid() );


-- ----------------------------------------------------------------
--  3. 변경 이력도 같은 규칙을 따릅니다
--
--     이력은 예약에 딸린 것이라, 볼 수 있는 예약의 이력만 봅니다.
--     고치기와 지우기는 여전히 막습니다. 이력은 남아야 합니다.
-- ----------------------------------------------------------------
drop policy if exists "이력 읽기" on booking_change;
drop policy if exists "이력 넣기" on booking_change;

create policy "이력 읽기" on booking_change
  for select
  using ( exists (
    select 1 from booking b
    where b.id = booking_change.booking_id
      and (b.user_id is null or b.user_id = auth.uid())
  ) );

create policy "이력 넣기" on booking_change
  for insert
  with check ( exists (
    select 1 from booking b
    where b.id = booking_change.booking_id
      and (b.user_id is null or b.user_id = auth.uid())
  ) );


-- ----------------------------------------------------------------
--  확인
-- ----------------------------------------------------------------
select
  count(*)                                   as 전체,
  count(*) filter (where user_id is null)    as 익명,
  count(*) filter (where user_id is not null) as 로그인
from booking;

# 真实模型与MySQL验收

执行时间：2026-11-26T11:06:17.252097+08:00
模型：qwen3.8-max
结果：8/8通过。

独立参考SQL与模型实际查询结果逐项比较；仅执行SELECT，没有写入或创建测试数据。模型随机性和实际数据变化会影响后续运行。

## PASS：记录数
成绩记录总共有多少条？返回一列record_count。

基准SQL：
```sql
SELECT COUNT(*) AS record_count FROM student_grades
```
实际SQL：
```sql
SELECT COUNT(*) AS record_count FROM student_grades
```
修正次数：0
错误：[]

## PASS：去重人数
学校一共有多少名学生？返回一列student_count，按学号去重。

基准SQL：
```sql
SELECT COUNT(DISTINCT student_id) AS student_count FROM student_grades
```
实际SQL：
```sql
SELECT COUNT(DISTINCT student_id) AS student_count FROM student_grades
```
修正次数：0
错误：[]

## PASS：各科均分
各科平均分是多少？返回subject和avg_score两列，保留2位小数。

基准SQL：
```sql
SELECT subject, ROUND(AVG(score),2) AS avg_score FROM student_grades GROUP BY subject
```
实际SQL：
```sql
SELECT subject, ROUND(AVG(score), 2) AS avg_score FROM student_grades GROUP BY subject
```
修正次数：0
错误：[]

## PASS：班级最高均分
全校平均分最高的班级是哪个？基于所有成绩记录，保留并列，返回class_name和avg_score两列，均分显示2位小数。

基准SQL：
```sql
WITH c AS (SELECT class_name,AVG(score) AS raw_avg FROM student_grades GROUP BY class_name) SELECT class_name,ROUND(raw_avg,2) AS avg_score FROM c WHERE raw_avg=(SELECT MAX(raw_avg) FROM c)
```
实际SQL：
```sql
WITH class_avg AS (SELECT class_name, AVG(score) AS avg_score_raw FROM student_grades GROUP BY class_name), ranked AS (SELECT class_name, avg_score_raw, RANK() OVER (ORDER BY avg_score_raw DESC) AS rnk FROM class_avg) SELECT class_name, ROUND(avg_score_raw, 2) AS avg_score FROM ranked WHERE rnk = 1
```
修正次数：0
错误：[]

## PASS：学期过滤
2025-2026学年第一学期各科平均分是多少？返回subject和avg_score两列，保留2位小数。

基准SQL：
```sql
SELECT subject,ROUND(AVG(score),2) AS avg_score FROM student_grades WHERE semester='2025-2026学年第一学期' GROUP BY subject
```
实际SQL：
```sql
SELECT subject, ROUND(AVG(score), 2) AS avg_score FROM student_grades WHERE semester = '2025-2026学年第一学期' GROUP BY subject
```
修正次数：0
错误：[]

## PASS：及格率
各科成绩记录的及格率是多少？60分及格，百分数保留2位小数，返回subject和pass_rate两列。

基准SQL：
```sql
SELECT subject, ROUND(100.0*SUM(CASE WHEN score>=60 THEN 1 ELSE 0 END)/COUNT(*),2) AS pass_rate FROM student_grades GROUP BY subject
```
实际SQL：
```sql
SELECT subject, ROUND(SUM(CASE WHEN score >= 60 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pass_rate FROM student_grades GROUP BY subject
```
修正次数：0
错误：[]

## PASS：分数分布
按全部成绩记录，统计不及格（低于60）、及格（60至低于90）、优秀（90及以上）三个分数段的记录数，返回score_band和record_count两列，只输出有数据的分数段。

基准SQL：
```sql
SELECT CASE WHEN score<60 THEN '不及格' WHEN score<90 THEN '及格' ELSE '优秀' END AS score_band, COUNT(*) AS record_count FROM student_grades GROUP BY score_band
```
实际SQL：
```sql
SELECT CASE WHEN score < 60 THEN '不及格' WHEN score >= 60 AND score < 90 THEN '及格' WHEN score >= 90 THEN '优秀' END AS score_band, COUNT(*) AS record_count FROM student_grades GROUP BY CASE WHEN score < 60 THEN '不及格' WHEN score >= 60 AND score < 90 THEN '及格' WHEN score >= 90 THEN '优秀' END
```
修正次数：0
错误：[]

## PASS：无数据
查询学号为__DEMO_MISSING_STUDENT__的学生成绩，返回student_id、subject、score三列。

基准SQL：
```sql
SELECT student_id,subject,score FROM student_grades WHERE student_id='__DEMO_MISSING_STUDENT__'
```
实际SQL：
```sql
SELECT student_id, subject, score FROM student_grades WHERE student_id = '__DEMO_MISSING_STUDENT__'
```
修正次数：0
错误：[]

## 最终验证补充

- 自动化测试：54通过，包含真实MySQL的百分号/冒号字面量、200行截断与小LIMIT保留。
- 浏览器：真实均分、SQL、表格、柱状图和执行轨迹已验证；原Dify仍可访问。
- 补充真实模型：折线图、饼图、拒绝写入3项通过。
- 独立代码审查发现6项问题已修复，其中5项有失败再通过的回归测试，另1项为披露修正。
- 不修改现有MySQL数据或权限。未提交/推送代码。
- 首版每个问题独立处理，不支持省略条件的跨轮追问；模型生成结果仍需结合SQL和表格核对。

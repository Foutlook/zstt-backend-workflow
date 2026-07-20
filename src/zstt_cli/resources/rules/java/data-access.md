# 数据访问与远程调用规则

## 触发条件

本次范围包含数据库、Mapper、Repository、RPC、HTTP、外部 API、列表、批量、图表、统计或聚合映射。

## 强约束

- 禁止 N+1 查询和循环远程调用。先收集批量参数，一次获取，再在内存映射或聚合。
- 不得在循环中按单 ID 重复调用 Mapper、Repository、RPC Client 或外部 API Client。
- 查询只取所需列，并明确分页、排序、逻辑删除、租户和权限范围。
- 聚合接口必须采用单一关系源：从一个上游关系源确定最终实体集，再从同一数据范围派生 ownership、章节、状态和响应映射。
- 两个来源的数据范围未被代码、Schema、查询或契约证明一致时，不得混用。
- 不增加 fallback 映射或平行查询来隐藏来源不一致；优先移除错误的来源分裂。

## 例子

错误：遍历 `chapterIds`，每次执行 `chapterMapper.selectById(id)`。

正确：一次 `selectByIds(chapterIds)`，构建 `Map<Long, Chapter>` 后组装结果。如果批量接口不存在，先明确契约缺口，不把 N+1 藏在实现里。

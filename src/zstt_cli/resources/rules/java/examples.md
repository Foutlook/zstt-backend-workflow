# ZSTT Java 后端细则

## 1. 主链路可读性

- public 方法体现业务顺序：校验、读取、计算、写入、通知和返回。
- 复杂链式调用、非显然计算、复用值或调试关键值才抽取局部变量。
- 简单 getter、常量、一层方法调用和直接返回保持内联。

## 2. 注释与日志

- 业务规则注释解释约束来源和不这样做的后果。
- 状态机、幂等、事务后通知、历史兼容和数据范围必须写清边界。
- 入口日志避免完整打印敏感请求；记录可定位业务实例的安全标识。
- 外部调用记录目标、关键身份、耗时、结果和失败位置。

## 3. Jackson 示例

```java
public class ProgressRequest {

    @JsonProperty("zValue")
    @JsonAlias("zvalue") // 仅在历史请求确实存在时保留
    private BigDecimal zValue;
}
```

配套测试至少证明：

1. `zValue` 可以反序列化；
2. 序列化只输出规范名称；
3. 不需要兼容时不会静默接受错误名称。

## 4. 批量查询示例

错误方向：在课程循环中逐条调用 `chapterMapper.selectById` 或 RPC。

正确方向：先收集 chapterId，一次批量获取，构建 `Map<Long, Chapter>` 后组装结果。无法提供批量接口时先在方案阶段明确契约缺口，不在实现阶段隐藏 N+1。

## 5. 聚合数据源

先画出：最终实体集来源、映射来源和最终赋值点。两套来源范围未被代码或契约证明一致时，不得混用。优先移除错误的来源分裂，而不是增加兜底映射。

## 6. Maven 本地验证

```text
mvn -pl <module> -am "-Dsmart-doc.phase=verify" -Dtest=<FocusedTest> "-Dsurefire.failIfNoSpecifiedTests=false" test
mvn -pl <module> -am "-Dsmart-doc.phase=verify" -DskipTests compile
```

只有任务本身是生成或验证 API 文档时，才有意执行 smart-doc 生命周期。

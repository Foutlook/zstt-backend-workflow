# Java 验证检查表

## 检查项

- 缺陷修复应先获得聚焦失败信号，再验证修复后信号。
- 新行为和高风险边界应增加或更新聚焦单测、ObjectMapper/MVC 测试、Mapper 测试或集成测试。
- 修改前后使用同一命令和判定口径；记录退出码、关键结果和未覆盖边界。
- 只执行编译或静态检查时，不得写成业务测试已通过。
- 无法运行关键验证时，说明环境、权限、数据或依赖阻塞，并给出可复现命令。
- Maven 项目若 smart-doc 绑定 `compile` 或 `test` 等早期阶段，而目标只是验证业务代码，命令传 `-Dsmart-doc.phase=verify`。
- 任务本身是生成或验证 API 文档时，不使用 smart-doc 绕过参数。

## 命令示例

```text
mvn -pl <module> -am "-Dsmart-doc.phase=verify" -Dtest=<FocusedTest> "-Dsurefire.failIfNoSpecifiedTests=false" test
mvn -pl <module> -am "-Dsmart-doc.phase=verify" -DskipTests compile
```

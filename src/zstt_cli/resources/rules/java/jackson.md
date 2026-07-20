# JavaBean 与 Jackson 规则

## 触发条件

本次范围包含 Jackson 序列化/反序列化的 DTO、VO、Request、Response 或接口契约。

## 强约束

- 首段是单字母或第二个字符为大写的字段属于高风险命名，例如 `zValue`、`pType`、`uId`、`eTag`、`aName`。
- 高风险字段必须显式声明规范 JSON 名称，例如 `@JsonProperty("zValue")`。
- 只有历史请求确实需要兼容时才添加 `@JsonAlias`；alias 不能替代规范属性名。
- 排查缺参时先区分“请求未发送”和“Jackson 没有按预期绑定”。
- 新增或修改高风险字段时，必须用 ObjectMapper 或 MVC 请求测试证明序列化和反序列化名称。

## 例子

```java
public class ProgressRequest {

    @JsonProperty("zValue")
    @JsonAlias("zvalue") // 只有真实历史请求需要时才保留
    private BigDecimal zValue;
}
```

测试至少证明：`zValue` 可反序列化、序列化只输出规范名称、不需要兼容时不会静默接受错误名称。

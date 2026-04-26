import { useEffect, useState } from "react";
import {
  Card, Form, Input, Button, message, Divider, Typography, Spin, Alert,
} from "antd";
import {
  SettingOutlined, SaveOutlined, ApiOutlined, RobotOutlined,
} from "@ant-design/icons";
import api from "../services/api";

const { Title, Text } = Typography;

interface ConfigItem {
  key: string;
  label: string;
  group: string;
  secret: boolean;
  value: string;
}

export default function SystemConfigPage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [items, setItems] = useState<ConfigItem[]>([]);

  useEffect(() => {
    loadConfig();
  }, []);

  async function loadConfig() {
    setLoading(true);
    try {
      const res = await api.get<{ items: ConfigItem[] }>("/system-config");
      setItems(res.data.items);
      const vals: Record<string, string> = {};
      for (const item of res.data.items) {
        vals[item.key] = item.value;
      }
      form.setFieldsValue(vals);
    } catch {
      message.error("加载系统配置失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      const values = await form.validateFields();
      await api.put("/system-config", { updates: values });
      message.success("配置已保存，下次问答时自动生效");
      await loadConfig(); // 重新加载以获取最新掩码值
    } catch (err: any) {
      if (err?.errorFields) return; // 表单校验错误
      message.error(err?.response?.data?.detail || "保存失败");
    } finally {
      setSaving(false);
    }
  }

  const knowledgeItems = items.filter((i) => i.group === "knowledge");

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "32px 24px" }}>
      <div style={{ marginBottom: 24, display: "flex", alignItems: "center", gap: 12 }}>
        <SettingOutlined style={{ fontSize: 24, color: "#52c41a" }} />
        <Title level={4} style={{ margin: 0 }}>系统配置</Title>
      </div>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
        message="配置优先级"
        description="此处保存的配置优先级高于服务器 .env 文件。敏感字段（API Key）显示为掩码，若不修改请保持原值或留空。"
      />

      <Form form={form} layout="vertical" onFinish={handleSave}>

        {/* 知识库配置 */}
        <Card
          title={
            <span>
              <ApiOutlined style={{ marginRight: 8, color: "#1677ff" }} />
              知识库配置（RAG 检索增强）
            </span>
          }
          style={{ marginBottom: 20 }}
        >
          {knowledgeItems.map((item) => (
            <Form.Item
              key={item.key}
              name={item.key}
              label={
                <span>
                  {item.label}
                  {item.secret && (
                    <Text type="secondary" style={{ fontSize: 12, marginLeft: 6 }}>
                      （敏感，显示掩码）
                    </Text>
                  )}
                </span>
              }
            >
              <Input
                placeholder={`请输入 ${item.label}`}
                type={item.secret ? "password" : "text"}
                allowClear={!item.secret}
                style={{ fontFamily: item.secret ? "monospace" : undefined }}
              />
            </Form.Item>
          ))}
        </Card>

        {/* LLM 配置 */}
        <Card
          title={
            <span>
              <RobotOutlined style={{ marginRight: 8, color: "#722ed1" }} />
              LLM 配置（大语言模型）
            </span>
          }
          style={{ marginBottom: 24 }}
        >
          <Form.Item
            name="llm_api_key"
            label={
              <span>
                LLM API Key
                <Text type="secondary" style={{ fontSize: 12, marginLeft: 6 }}>（敏感，显示掩码）</Text>
              </span>
            }
          >
            <Input.Password placeholder="请输入 LLM API Key" style={{ fontFamily: "monospace" }} />
          </Form.Item>

          <Form.Item name="llm_base_url" label="LLM Base URL（OpenAI 兼容接口）">
            <Input placeholder="例：https://api.deepseek.com" />
          </Form.Item>

          <Form.Item name="llm_model" label="LLM 模型名称">
            <Input placeholder="例：deepseek-v4-flash" />
          </Form.Item>
        </Card>

        <Divider />

        <Form.Item style={{ textAlign: "right", marginBottom: 0 }}>
          <Button
            type="primary"
            htmlType="submit"
            icon={<SaveOutlined />}
            loading={saving}
            size="large"
          >
            保存配置
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
}

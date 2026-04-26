import { useState } from "react";
import { Card, Button, Tag, Space, Typography, List, Tooltip, message } from "antd";
import { CalendarOutlined, CheckOutlined, CloseOutlined, BellOutlined } from "@ant-design/icons";
import { ProposedReminder, batchCreateReminders } from "../services/api";

const { Text } = Typography;

interface Props {
  summary: string;
  reminders: ProposedReminder[];
  onConfirmed: () => void;
  onDismissed: () => void;
}

export default function ReminderProposalCard({ summary, reminders, onConfirmed, onDismissed }: Props) {
  const [loading, setLoading] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  if (dismissed || confirmed) return null;

  async function handleConfirm() {
    setLoading(true);
    try {
      await batchCreateReminders(reminders);
      setConfirmed(true);
      message.success(`已添加 ${reminders.length} 条农事提醒到日历`);
      onConfirmed();
    } catch {
      message.error("添加提醒失败，请重试");
    } finally {
      setLoading(false);
    }
  }

  function handleDismiss() {
    setDismissed(true);
    onDismissed();
  }

  return (
    <Card
      size="small"
      style={{
        marginTop: 12,
        border: "1px solid #91caff",
        borderRadius: 10,
        background: "#f0f7ff",
      }}
      bodyStyle={{ padding: "12px 16px" }}
    >
      {/* 标题行 */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <BellOutlined style={{ color: "#1677ff", fontSize: 16 }} />
        <Text strong style={{ color: "#1677ff" }}>AI 建议添加农事提醒</Text>
        <Tag color="blue" style={{ marginLeft: "auto" }}>{reminders.length} 条</Tag>
      </div>

      {/* 摘要 */}
      <Text type="secondary" style={{ fontSize: 13, display: "block", marginBottom: 10 }}>
        {summary}
      </Text>

      {/* 提醒列表（最多显示5条，其余折叠） */}
      <List
        size="small"
        dataSource={reminders.slice(0, 5)}
        style={{ marginBottom: 4 }}
        renderItem={(item) => (
          <List.Item style={{ padding: "4px 0", borderBottom: "none" }}>
            <Space size={8}>
              <CalendarOutlined style={{ color: "#52c41a" }} />
              <Tag color="green" style={{ fontSize: 12 }}>
                {item.scheduled_date}
              </Tag>
              <Tooltip
                title={
                  <div>
                    <div>{item.task_description}</div>
                    {item.operation_steps && (
                      <div style={{ marginTop: 4, color: "#aaa" }}>
                        操作：{item.operation_steps}
                      </div>
                    )}
                    {item.key_notes && (
                      <div style={{ marginTop: 4, color: "#faad14" }}>
                        注意：{item.key_notes}
                      </div>
                    )}
                  </div>
                }
                placement="right"
              >
                <Text style={{ fontSize: 13, cursor: "default" }}>{item.title}</Text>
              </Tooltip>
            </Space>
          </List.Item>
        )}
      />
      {reminders.length > 5 && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          ...还有 {reminders.length - 5} 条（确认后在日历中查看）
        </Text>
      )}

      {/* 操作按钮 */}
      <div style={{ display: "flex", gap: 8, marginTop: 12, justifyContent: "flex-end" }}>
        <Button size="small" icon={<CloseOutlined />} onClick={handleDismiss}>
          不需要
        </Button>
        <Button
          size="small"
          type="primary"
          icon={<CheckOutlined />}
          loading={loading}
          onClick={handleConfirm}
        >
          确认添加到日历
        </Button>
      </div>
    </Card>
  );
}

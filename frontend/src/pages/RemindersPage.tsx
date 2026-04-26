import { useState, useEffect, useCallback } from "react";
import {
  Badge, Calendar, Card, Typography, Tag, Space, Button, Drawer,
  List, Checkbox, Popconfirm, message, Empty, Spin,
} from "antd";
import type { CalendarProps } from "antd";
import type { Dayjs } from "dayjs";
import dayjs from "dayjs";
import "dayjs/locale/zh-cn";
import {
  CalendarOutlined, DeleteOutlined, ReloadOutlined,
  EnvironmentOutlined, TagOutlined,
} from "@ant-design/icons";
import { listReminders, toggleReminderDone, deleteReminder, type ReminderDTO } from "../services/api";

const { Title, Text, Paragraph } = Typography;

dayjs.locale("zh-cn");

export default function RemindersPage() {
  const today = dayjs();
  const [currentMonth, setCurrentMonth] = useState({ year: today.year(), month: today.month() + 1 });
  const [reminders, setReminders] = useState<ReminderDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [selectedReminders, setSelectedReminders] = useState<ReminderDTO[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listReminders(currentMonth.year, currentMonth.month);
      setReminders(res.data);
    } catch {
      message.error("加载提醒失败");
    } finally {
      setLoading(false);
    }
  }, [currentMonth]);

  useEffect(() => { load(); }, [load]);

  // 按日期分组
  const byDate = reminders.reduce<Record<string, ReminderDTO[]>>((acc, r) => {
    const d = r.scheduled_date;
    if (!acc[d]) acc[d] = [];
    acc[d].push(r);
    return acc;
  }, {});

  function openDay(dateStr: string) {
    setSelectedDate(dateStr);
    setSelectedReminders(byDate[dateStr] || []);
    setDrawerOpen(true);
  }

  async function handleToggle(id: number) {
    try {
      const res = await toggleReminderDone(id);
      setReminders((prev) =>
        prev.map((r) => (r.id === id ? { ...r, is_done: res.data.is_done } : r))
      );
      // 同步 drawer 中的列表
      setSelectedReminders((prev) =>
        prev.map((r) => (r.id === id ? { ...r, is_done: res.data.is_done } : r))
      );
    } catch {
      message.error("操作失败");
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteReminder(id);
      setReminders((prev) => prev.filter((r) => r.id !== id));
      setSelectedReminders((prev) => prev.filter((r) => r.id !== id));
      message.success("提醒已删除");
    } catch {
      message.error("删除失败");
    }
  }

  // Calendar cell renderer
  const cellRender: CalendarProps<Dayjs>["cellRender"] = (value) => {
    const dateStr = value.format("YYYY-MM-DD");
    const dayReminders = byDate[dateStr] || [];
    if (!dayReminders.length) return null;

    const doneCount = dayReminders.filter((r) => r.is_done).length;
    const allDone = doneCount === dayReminders.length;

    return (
      <div
        style={{ cursor: "pointer" }}
        onClick={(e) => { e.stopPropagation(); openDay(dateStr); }}
      >
        <Badge
          count={dayReminders.length}
          color={allDone ? "#52c41a" : "#1677ff"}
          size="small"
          style={{ fontSize: 10 }}
        />
        <div style={{ marginTop: 2 }}>
          {dayReminders.slice(0, 2).map((r) => (
            <div
              key={r.id}
              style={{
                fontSize: 11,
                lineHeight: "16px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                color: r.is_done ? "#aaa" : "#333",
                textDecoration: r.is_done ? "line-through" : "none",
              }}
            >
              • {r.title}
            </div>
          ))}
          {dayReminders.length > 2 && (
            <div style={{ fontSize: 11, color: "#999" }}>
              +{dayReminders.length - 2} 更多
            </div>
          )}
        </div>
      </div>
    );
  };

  const totalCount = reminders.length;
  const doneCount = reminders.filter((r) => r.is_done).length;
  const overdueCount = reminders.filter(
    (r) => !r.is_done && r.scheduled_date < today.format("YYYY-MM-DD")
  ).length;

  return (
    <div style={{ padding: "24px 32px", height: "100%", overflow: "auto" }}>
      {/* 头部 */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <CalendarOutlined style={{ fontSize: 24, color: "#52c41a" }} />
          <Title level={4} style={{ margin: 0 }}>农事日历提醒</Title>
        </div>
        <Space>
          {overdueCount > 0 && (
            <Tag color="red">逾期未完成 {overdueCount} 条</Tag>
          )}
          <Tag color="blue">本月共 {totalCount} 条</Tag>
          <Tag color="green">已完成 {doneCount} 条</Tag>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading} size="small">
            刷新
          </Button>
        </Space>
      </div>

      {/* 日历 */}
      <Spin spinning={loading}>
        <Card bodyStyle={{ padding: 0 }}>
          <Calendar
            cellRender={cellRender}
            onPanelChange={(value) => {
              setCurrentMonth({ year: value.year(), month: value.month() + 1 });
            }}
            onSelect={(value) => {
              const dateStr = value.format("YYYY-MM-DD");
              if (byDate[dateStr]?.length) openDay(dateStr);
            }}
          />
        </Card>
      </Spin>

      {/* 日期详情抽屉 */}
      <Drawer
        title={
          <Space>
            <CalendarOutlined style={{ color: "#1677ff" }} />
            <span>{selectedDate} 农事提醒</span>
            <Tag>{selectedReminders.length} 条</Tag>
          </Space>
        }
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={480}
        bodyStyle={{ padding: "16px 20px" }}
      >
        {selectedReminders.length === 0 ? (
          <Empty description="当日无提醒" />
        ) : (
          <List
            dataSource={selectedReminders}
            renderItem={(r) => (
              <Card
                key={r.id}
                size="small"
                style={{
                  marginBottom: 12,
                  opacity: r.is_done ? 0.65 : 1,
                  border: r.is_done ? "1px solid #d9d9d9" : "1px solid #91caff",
                  background: r.is_done ? "#fafafa" : "#f0f7ff",
                }}
              >
                {/* 标题行 */}
                <div style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
                  <Checkbox
                    checked={r.is_done}
                    onChange={() => handleToggle(r.id)}
                  />
                  <Text
                    strong
                    style={{
                      flex: 1,
                      textDecoration: r.is_done ? "line-through" : "none",
                      color: r.is_done ? "#aaa" : "#222",
                    }}
                  >
                    {r.title}
                  </Text>
                  <Popconfirm
                    title="确认删除此提醒？"
                    onConfirm={() => handleDelete(r.id)}
                    okText="删除"
                    cancelText="取消"
                  >
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                    />
                  </Popconfirm>
                </div>

                {/* 区域/作物标签 */}
                {(r.region_name || r.crop_name) && (
                  <Space size={4} style={{ marginBottom: 8 }}>
                    {r.region_name && (
                      <Tag icon={<EnvironmentOutlined />} color="green" style={{ fontSize: 11 }}>
                        {r.region_name}
                      </Tag>
                    )}
                    {r.crop_name && (
                      <Tag icon={<TagOutlined />} color="cyan" style={{ fontSize: 11 }}>
                        {r.crop_name}
                      </Tag>
                    )}
                  </Space>
                )}

                {/* 任务描述 */}
                {r.task_description && (
                  <Paragraph style={{ fontSize: 13, margin: "4px 0", color: "#444" }}>
                    📋 {r.task_description}
                  </Paragraph>
                )}

                {/* 操作步骤 */}
                {r.operation_steps && (
                  <Paragraph style={{ fontSize: 12, margin: "4px 0", color: "#555" }}>
                    🔧 {r.operation_steps}
                  </Paragraph>
                )}

                {/* 注意要领 */}
                {r.key_notes && (
                  <Paragraph style={{ fontSize: 12, margin: "4px 0", color: "#d46b08" }}>
                    ⚠️ {r.key_notes}
                  </Paragraph>
                )}
              </Card>
            )}
          />
        )}
      </Drawer>
    </div>
  );
}

import { useState, useEffect, useRef } from "react";
import {
  Layout, List, Button, Input, Typography, Spin, Empty,
  message, Popconfirm, Avatar, Space, Badge, Tag,
} from "antd";
import {
  PlusOutlined, DeleteOutlined, SendOutlined,
  UserOutlined, RobotOutlined, BulbOutlined,
} from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  listConversations, getConversation, askInConversation,
  deleteConversation, getCropPhenology,
  listMemoryProposals,
  type ConversationDTO, type MessageDTO, type ProposedReminder,
} from "../services/api";
import NewConversationModal from "../components/NewConversationModal";
import MemoryProposalModal from "../components/MemoryProposalModal";
import MemoryPanel from "../components/MemoryPanel";
import ReminderProposalCard from "../components/ReminderProposalCard";

const { Sider, Content } = Layout;
const { Text } = Typography;
const { TextArea } = Input;

const QUICK_QUESTIONS = [
  "现在该施什么肥？",
  "最近常见的病虫害有哪些？",
  "什么时候浇水合适？",
  "最近需要注意的田间管理？",
];

export default function ChatPage() {
  const [conversations, setConversations] = useState<ConversationDTO[]>([]);
  const [active, setActive] = useState<ConversationDTO | null>(null);
  const [messages, setMessages] = useState<MessageDTO[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [newModalOpen, setNewModalOpen] = useState(false);
  const [proposalModalOpen, setProposalModalOpen] = useState(false);
  const [pendingProposalCount, setPendingProposalCount] = useState(0);
  const [phenologyStage, setPhenologyStage] = useState<string | null>(null);
  const [memoryReloadToken, setMemoryReloadToken] = useState(0);
  // key = message_id, value = pending reminders for that message
  const [pendingReminders, setPendingReminders] = useState<Record<number, { summary: string; items: ProposedReminder[] }>>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadList = async () => {
    try {
      const { data } = await listConversations();
      setConversations(data);
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => { loadList(); }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 切换对话时，加载消息、物候期、待确认提案数
  useEffect(() => {
    if (!active) {
      setMessages([]);
      setPhenologyStage(null);
      setPendingProposalCount(0);
      return;
    }
    (async () => {
      const { data } = await getConversation(active.id);
      setMessages(data.messages);

      // 物候期
      try {
        const { data: phen } = await getCropPhenology(active.crop_id, active.region_id);
        setPhenologyStage(phen.current_stage?.stage_name ?? null);
      } catch { setPhenologyStage(null); }

      // 待确认提案
      try {
        const { data: props } = await listMemoryProposals(active.id);
        setPendingProposalCount(props.length);
      } catch { setPendingProposalCount(0); }
    })();
  }, [active]);

  const handleSend = async (text?: string) => {
    const q = (text ?? question).trim();
    if (!q) return;
    if (!active) {
      message.warning("请先新建对话并选择区域和作物");
      setNewModalOpen(true);
      return;
    }
    setQuestion("");
    setLoading(true);

    const optimistic: MessageDTO = {
      id: Date.now(), role: "user", content: q,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);

    try {
      const { data } = await askInConversation(active.id, q);
      setMessages((prev) => [
        ...prev,
        {
          id: data.message_id, role: "assistant", content: data.answer,
          created_at: new Date().toISOString(),
        },
      ]);
      if (data.phenology_stage) setPhenologyStage(data.phenology_stage);

      // 提醒候选：绑定到本条消息 ID
      if (data.proposed_reminders?.length && data.reminder_summary) {
        setPendingReminders((prev) => ({
          ...prev,
          [data.message_id]: {
            summary: data.reminder_summary,
            items: data.proposed_reminders,
          },
        }));
      }

      const newProposals = data.proposal_ids?.length ?? 0;
      if (newProposals > 0) {
        setPendingProposalCount((c) => c + newProposals);
        message.info({
          content: (
            <Space>
              <BulbOutlined style={{ color: "#faad14" }} />
              AI 识别到 {newProposals} 条新信息，点右上角「待确认」查看
            </Space>
          ),
          duration: 4,
        });
      }
      await loadList();
    } catch (err: any) {
      message.error(err.response?.data?.detail || "提问失败，请重试");
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number, e?: React.MouseEvent) => {
    e?.stopPropagation();
    await deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (active?.id === id) setActive(null);
    message.success("对话已删除");
  };

  const handleCreated = (conv: any) => {
    setNewModalOpen(false);
    setConversations((prev) => [conv, ...prev]);
    setActive(conv);
  };

  const refreshProposalsAndMemory = async () => {
    if (!active) return;
    try {
      const { data } = await listMemoryProposals(active.id);
      setPendingProposalCount(data.length);
    } catch { /* ignore */ }
    setMemoryReloadToken((t) => t + 1);
  };

  return (
    <Layout style={{ height: "calc(100vh - 56px)" }}>
      {/* 左侧对话列表 */}
      <Sider
        width={240} theme="light"
        style={{ borderRight: "1px solid #f0f0f0", overflow: "auto" }}
      >
        <div style={{ padding: 12 }}>
          <Button
            type="primary" icon={<PlusOutlined />} block
            onClick={() => setNewModalOpen(true)}
          >
            新建咨询
          </Button>
        </div>
        {listLoading ? (
          <div style={{ textAlign: "center", padding: 24 }}><Spin /></div>
        ) : (
          <List
            dataSource={conversations}
            locale={{ emptyText: "暂无对话" }}
            renderItem={(conv) => (
              <List.Item
                style={{
                  padding: "8px 12px", cursor: "pointer",
                  background: active?.id === conv.id ? "#f6ffed" : "transparent",
                  borderLeft: active?.id === conv.id
                    ? "3px solid #52c41a" : "3px solid transparent",
                }}
                onClick={() => setActive(conv)}
                actions={[
                  <Popconfirm
                    title="确定删除此对话？"
                    onConfirm={(e) => handleDelete(conv.id, e as any)}
                    onPopupClick={(e: any) => e.stopPropagation()}
                  >
                    <Button
                      type="text" size="small" danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </Popconfirm>,
                ]}
              >
                <Text ellipsis style={{ maxWidth: 150, fontSize: 13 }}>
                  {conv.title}
                </Text>
              </List.Item>
            )}
          />
        )}
      </Sider>

      {/* 中间消息区 */}
      <Content style={{ display: "flex", flexDirection: "column" }}>
        {/* 顶部信息条 */}
        {active && (
          <div
            style={{
              padding: "10px 24px", background: "#fafafa",
              borderBottom: "1px solid #f0f0f0",
              display: "flex", justifyContent: "space-between", alignItems: "center",
            }}
          >
            <Space size="middle">
              <Text strong>{active.title}</Text>
              {phenologyStage && <Tag color="orange">🌱 当前物候期：{phenologyStage}</Tag>}
            </Space>
            <Badge count={pendingProposalCount} size="small">
              <Button
                size="small" icon={<BulbOutlined />}
                onClick={() => setProposalModalOpen(true)}
                disabled={pendingProposalCount === 0}
              >
                待确认记忆
              </Button>
            </Badge>
          </div>
        )}

        {/* 消息列表 */}
        <div style={{ flex: 1, overflow: "auto", padding: "24px 48px" }}>
          {!active ? (
            <Empty
              image={<span style={{ fontSize: 64, lineHeight: 1 }}>🌾</span>}
              imageStyle={{ height: "auto", marginBottom: 8 }}
              description={
                <span>
                  欢迎使用农户种植技巧问答系统
                  <br />
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    请点击左侧「新建咨询」，选择您的地区和作物开始问答
                  </Text>
                </span>
              }
              style={{ marginTop: 80 }}
            >
              <Button type="primary" onClick={() => setNewModalOpen(true)}>
                立即新建咨询
              </Button>
            </Empty>
          ) : messages.length === 0 ? (
            <div style={{ textAlign: "center", marginTop: 40 }}>
              <Text type="secondary">您可以先试试下面的快捷问题：</Text>
              <div style={{ marginTop: 16 }}>
                <Space wrap>
                  {QUICK_QUESTIONS.map((q) => (
                    <Button key={q} onClick={() => handleSend(q)}>
                      {q}
                    </Button>
                  ))}
                </Space>
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: "flex", gap: 12, marginBottom: 24,
                  flexDirection: msg.role === "user" ? "row-reverse" : "row",
                  alignItems: "flex-start",
                }}
              >
                <Avatar
                  icon={msg.role === "user" ? <UserOutlined /> : <RobotOutlined />}
                  style={{
                    backgroundColor: msg.role === "user" ? "#52c41a" : "#1677ff",
                    flexShrink: 0,
                  }}
                />
                <div style={{ maxWidth: "72%", minWidth: 0 }}>
                  <div
                    style={{
                      padding: "10px 14px", borderRadius: 12,
                      background: msg.role === "user" ? "#f6ffed" : "#fff",
                      border: "1px solid",
                      borderColor: msg.role === "user" ? "#b7eb8f" : "#f0f0f0",
                      lineHeight: 1.6,
                    }}
                  >
                    {msg.role === "user" ? (
                      <span style={{ whiteSpace: "pre-wrap" }}>{msg.content}</span>
                    ) : (
                      <div className="markdown-body">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                  {/* 提醒确认卡片（仅 assistant 消息，有候选时展示） */}
                  {msg.role === "assistant" && pendingReminders[msg.id] && (
                    <ReminderProposalCard
                      summary={pendingReminders[msg.id].summary}
                      reminders={pendingReminders[msg.id].items}
                      onConfirmed={() =>
                        setPendingReminders((prev) => {
                          const next = { ...prev };
                          delete next[msg.id];
                          return next;
                        })
                      }
                      onDismissed={() =>
                        setPendingReminders((prev) => {
                          const next = { ...prev };
                          delete next[msg.id];
                          return next;
                        })
                      }
                    />
                  )}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
              <Avatar icon={<RobotOutlined />} style={{ backgroundColor: "#1677ff" }} />
              <div style={{ padding: "10px 14px", borderRadius: 12, background: "#fff", border: "1px solid #f0f0f0" }}>
                <Spin size="small" /> 正在思考中...
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* 输入区 */}
        <div
          style={{
            padding: "12px 48px 24px", borderTop: "1px solid #f0f0f0",
            background: "#fff",
          }}
        >
          <Space.Compact style={{ width: "100%" }}>
            <TextArea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={
                active
                  ? "请输入您的种植问题，按 Ctrl+Enter 发送..."
                  : "请先新建咨询对话"
              }
              autoSize={{ minRows: 1, maxRows: 4 }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && e.ctrlKey) handleSend();
              }}
              style={{ borderRadius: "6px 0 0 6px" }}
              disabled={!active}
            />
            <Button
              type="primary" icon={<SendOutlined />}
              onClick={() => handleSend()} loading={loading}
              disabled={!active}
              style={{ height: "auto", borderRadius: "0 6px 6px 0" }}
            >
              发送
            </Button>
          </Space.Compact>
        </div>
      </Content>

      {/* 右侧记忆面板 */}
      <Sider
        width={260} theme="light"
        style={{ borderLeft: "1px solid #f0f0f0", background: "#fafafa", overflow: "auto" }}
      >
        <MemoryPanel
          regionId={active?.region_id ?? null}
          cropId={active?.crop_id ?? null}
          regionName={active?.title?.split("·")[0]}
          cropName={active?.title?.split("·")[1]}
          phenologyStage={phenologyStage}
          reloadToken={memoryReloadToken}
        />
      </Sider>

      <NewConversationModal
        open={newModalOpen}
        onClose={() => setNewModalOpen(false)}
        onCreated={handleCreated}
      />
      {active && (
        <MemoryProposalModal
          open={proposalModalOpen}
          conversationId={active.id}
          onClose={() => setProposalModalOpen(false)}
          onProcessed={refreshProposalsAndMemory}
        />
      )}
    </Layout>
  );
}

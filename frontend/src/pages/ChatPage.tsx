import { useState, useEffect, useRef } from "react";
import {
  Layout, List, Button, Input, Typography, Spin, Empty,
  message, Popconfirm, Avatar, Space,
} from "antd";
import {
  PlusOutlined, DeleteOutlined, SendOutlined,
  UserOutlined, RobotOutlined,
} from "@ant-design/icons";
import {
  listConversations, getConversation,
  askQuestion, deleteConversation,
} from "../services/api";

const { Sider, Content } = Layout;
const { Text } = Typography;
const { TextArea } = Input;

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

interface Conversation {
  id: number;
  title: string;
  updated_at: string;
}

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(true);
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

  const selectConversation = async (id: number) => {
    setActiveId(id);
    const { data } = await getConversation(id);
    setMessages(data.messages);
  };

  const handleNewChat = () => {
    setActiveId(null);
    setMessages([]);
  };

  const handleSend = async () => {
    if (!question.trim()) return;
    const q = question.trim();
    setQuestion("");
    setLoading(true);

    const optimisticMsg: Message = {
      id: Date.now(),
      role: "user",
      content: q,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMsg]);

    try {
      const { data } = await askQuestion(q, activeId ?? undefined);
      if (!activeId) {
        setActiveId(data.conversation_id);
        await loadList();
      }
      setMessages((prev) => [
        ...prev,
        { id: data.message_id, role: "assistant", content: data.answer, created_at: new Date().toISOString() },
      ]);
    } catch {
      message.error("提问失败，请重试");
      setMessages((prev) => prev.filter((m) => m.id !== optimisticMsg.id));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number, e?: React.MouseEvent) => {
    e?.stopPropagation();
    await deleteConversation(id);
    if (activeId === id) { setActiveId(null); setMessages([]); }
    setConversations((prev) => prev.filter((c) => c.id !== id));
    message.success("对话已删除");
  };

  return (
    <Layout style={{ height: "calc(100vh - 56px)" }}>
      <Sider
        width={240}
        theme="light"
        style={{ borderRight: "1px solid #f0f0f0", overflow: "auto" }}
      >
        <div style={{ padding: 12 }}>
          <Button icon={<PlusOutlined />} block onClick={handleNewChat}>
            新对话
          </Button>
        </div>
        {listLoading ? (
          <div style={{ textAlign: "center", padding: 24 }}><Spin /></div>
        ) : (
          <List
            dataSource={conversations}
            renderItem={(conv) => (
              <List.Item
                style={{
                  padding: "8px 12px",
                  cursor: "pointer",
                  background: activeId === conv.id ? "#f6ffed" : "transparent",
                  borderLeft: activeId === conv.id ? "3px solid #52c41a" : "3px solid transparent",
                }}
                onClick={() => selectConversation(conv.id)}
                actions={[
                  <Popconfirm
                    title="确定删除此对话？"
                    onConfirm={(e) => handleDelete(conv.id, e as any)}
                    onPopupClick={(e) => e.stopPropagation()}
                  >
                    <Button
                      type="text"
                      size="small"
                      icon={<DeleteOutlined />}
                      danger
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

      <Content style={{ display: "flex", flexDirection: "column" }}>
        {/* 消息区 */}
        <div style={{ flex: 1, overflow: "auto", padding: "24px 48px" }}>
          {messages.length === 0 ? (
            <Empty
              image="🌾"
              imageStyle={{ fontSize: 64, height: "auto" }}
              description={
                <span>
                  欢迎使用农户种植技巧问答系统
                  <br />
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    您可以询问施肥、病虫害防治、播种时间等种植相关问题
                  </Text>
                </span>
              }
              style={{ marginTop: 80 }}
            />
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: "flex",
                  gap: 12,
                  marginBottom: 24,
                  flexDirection: msg.role === "user" ? "row-reverse" : "row",
                }}
              >
                <Avatar
                  icon={msg.role === "user" ? <UserOutlined /> : <RobotOutlined />}
                  style={{
                    backgroundColor: msg.role === "user" ? "#52c41a" : "#1677ff",
                    flexShrink: 0,
                  }}
                />
                <div
                  style={{
                    maxWidth: "70%",
                    padding: "10px 14px",
                    borderRadius: 12,
                    background: msg.role === "user" ? "#f6ffed" : "#fff",
                    border: "1px solid",
                    borderColor: msg.role === "user" ? "#b7eb8f" : "#f0f0f0",
                    whiteSpace: "pre-wrap",
                    lineHeight: 1.6,
                  }}
                >
                  {msg.content}
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
        <div style={{ padding: "12px 48px 24px", borderTop: "1px solid #f0f0f0", background: "#fff" }}>
          <Space.Compact style={{ width: "100%" }}>
            <TextArea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="请输入您的种植问题，按 Ctrl+Enter 发送..."
              autoSize={{ minRows: 1, maxRows: 4 }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && e.ctrlKey) handleSend();
              }}
              style={{ borderRadius: "6px 0 0 6px" }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={loading}
              style={{ height: "auto", borderRadius: "0 6px 6px 0" }}
            >
              发送
            </Button>
          </Space.Compact>
        </div>
      </Content>
    </Layout>
  );
}

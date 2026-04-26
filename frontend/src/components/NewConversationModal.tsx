import { useState } from "react";
import { Modal, Form, Input, message, Typography, Space, Tag } from "antd";
import RegionSelector from "./RegionSelector";
import CropSelector from "./CropSelector";
import { createConversation, type RegionDTO, type CropDTO } from "../services/api";

const { Text } = Typography;

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (conversation: {
    id: number; title: string; region_id: number; crop_id: number;
  }) => void;
}

export default function NewConversationModal({ open, onClose, onCreated }: Props) {
  const [regionId, setRegionId] = useState<number | null>(null);
  const [region, setRegion] = useState<RegionDTO | null>(null);
  const [cropId, setCropId] = useState<number | null>(null);
  const [crop, setCrop] = useState<CropDTO | null>(null);
  const [title, setTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const reset = () => {
    setRegionId(null); setRegion(null);
    setCropId(null); setCrop(null);
    setTitle(""); setSubmitting(false);
  };

  const handleOk = async () => {
    if (!regionId || !cropId) {
      message.warning("请先选择区域和作物");
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await createConversation(
        regionId, cropId, title.trim() || undefined
      );
      message.success("对话已创建");
      onCreated(data);
      reset();
    } catch (err: any) {
      message.error(err.response?.data?.detail || "创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    reset();
    onClose();
  };

  return (
    <Modal
      title="🌾 新建种植咨询对话"
      open={open}
      onOk={handleOk}
      onCancel={handleCancel}
      confirmLoading={submitting}
      okText="开始咨询"
      cancelText="取消"
      width={560}
      destroyOnClose
    >
      <Text type="secondary" style={{ fontSize: 13 }}>
        请先选择您的所在地区和咨询的作物，系统将为您匹配本地化的种植建议。
      </Text>
      <Form layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item
          label={<span>所在地区 <Text type="danger">*</Text></span>}
          required
        >
          <RegionSelector
            value={regionId}
            onChange={(id, r) => { setRegionId(id); setRegion(r); }}
          />
          {region?.agro_zone && (
            <Tag color="green" style={{ marginTop: 6, fontSize: 11 }}>
              农业气候区: {region.agro_zone}
            </Tag>
          )}
        </Form.Item>

        <Form.Item
          label={<span>咨询作物 <Text type="danger">*</Text></span>}
          required
        >
          <CropSelector
            value={cropId}
            onChange={(id, c) => { setCropId(id); setCrop(c); }}
          />
        </Form.Item>

        <Form.Item label="对话标题 (可选)">
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={
              region && crop ? `${region.name}·${crop.name}` : "例如：老张家玉米大田"
            }
            maxLength={64}
            showCount
          />
        </Form.Item>

        {region && crop && (
          <Space
            style={{
              padding: "8px 12px", background: "#f6ffed",
              border: "1px solid #b7eb8f", borderRadius: 6, width: "100%",
            }}
          >
            <Text style={{ fontSize: 13 }}>
              📍 <Text strong>{region.full_name}</Text>
              {" · "}
              🌱 <Text strong>{crop.name}</Text>
            </Text>
          </Space>
        )}
      </Form>
    </Modal>
  );
}

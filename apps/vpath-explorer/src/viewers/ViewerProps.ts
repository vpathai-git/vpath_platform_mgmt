export type ViewerProps = {
  filename: string;
  contentUrl: string;
  size: number;
  onClose: () => void;
  onDownload: () => void;
};

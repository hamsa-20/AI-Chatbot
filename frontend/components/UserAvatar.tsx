interface Props {
  name: string;
  size?: 'sm' | 'md';
}

export default function UserAvatar({ name, size = 'md' }: Props) {
  const initials = name
    .split(' ')
    .map(w => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const sz = size === 'sm' ? 'w-7 h-7 text-xs' : 'w-9 h-9 text-sm';

  return (
    <div
      className={`${sz} rounded-full flex items-center justify-center font-semibold shrink-0
        bg-gradient-to-br from-[#3b7eff] to-[#6366f1] text-white select-none`}
    >
      {initials}
    </div>
  );
}
import {
  Check,
  X,
  Clock,
  Bell,
  BellRinging,
  CaretRight,
  CaretDown,
  Plus,
  MagnifyingGlass,
  Gear,
  Trash,
  PencilSimple,
  ArrowRight,
  CheckCircle,
} from '@phosphor-icons/react'

const SZ = 14
const WT = 'regular' as const

export const IconCheck = (p: any) => <Check size={SZ} weight={WT} {...p} />
export const IconX = (p: any) => <X size={SZ} weight={WT} {...p} />
export const IconClock = (p: any) => <Clock size={SZ} weight={WT} {...p} />
export const IconBell = (p: any) => <Bell size={SZ} weight={WT} {...p} />
export const IconBellRinging = (p: any) => <BellRinging size={SZ} weight={WT} {...p} />
export const IconChevRight = (p: any) => <CaretRight size={SZ} weight={WT} {...p} />
export const IconChevDown = (p: any) => <CaretDown size={SZ} weight={WT} {...p} />
export const IconPlus = (p: any) => <Plus size={SZ} weight={WT} {...p} />
export const IconSearch = (p: any) => <MagnifyingGlass size={SZ} weight={WT} {...p} />
export const IconGear = (p: any) => <Gear size={SZ} weight={WT} {...p} />
export const IconTrash = (p: any) => <Trash size={SZ} weight={WT} {...p} />
export const IconEdit = (p: any) => <PencilSimple size={SZ} weight={WT} {...p} />
export const IconArrowRight = (p: any) => <ArrowRight size={SZ} weight={WT} {...p} />
export const IconCheckCircle = (p: any) => <CheckCircle size={SZ} weight={WT} {...p} />

import { useNavigate } from 'react-router-dom'
import GenerationFlow from '@/components/GenerationFlow'

export default function GenerationCreatePage() {
  const navigate = useNavigate()

  const handleClose = () => {
    navigate('/generations')
  }

  return (
    <GenerationFlow
      onClose={handleClose}
    />
  )
}

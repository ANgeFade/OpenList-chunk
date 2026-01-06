import { Error, FullLoading, ImageWithError } from "~/components"
import { useRouter, useT } from "~/hooks"
import { objStore } from "~/store"
import { Obj, ObjType } from "~/types"
import { onCleanup, onMount } from "solid-js"

interface PreviewProps {
  images?: Obj[]
  navigate?: (name: string) => void
}

const Preview = (props: PreviewProps) => {
  const t = useT()
  const { replace } = useRouter()
  let images =
    props.images || objStore.objs.filter((obj) => obj.type === ObjType.IMAGE)
  if (images.length === 0) {
    images = [objStore.obj]
  }

  const prev = () => {
    const index = images.findIndex((f) => f.name === objStore.obj.name)
    if (index > 0) {
      if (props.navigate) {
        props.navigate(images[index - 1].name)
      } else {
        replace(images[index - 1].name)
      }
    }
  }

  const next = () => {
    const index = images.findIndex((f) => f.name === objStore.obj.name)
    if (index < images.length - 1) {
      if (props.navigate) {
        props.navigate(images[index + 1].name)
      } else {
        replace(images[index + 1].name)
      }
    }
  }

  const onKeydown = (e: KeyboardEvent) => {
    if (e.key === "ArrowLeft") {
      prev()
    } else if (e.key === "ArrowRight") {
      next()
    }
  }
  onMount(() => {
    window.addEventListener("keydown", onKeydown)
  })
  onCleanup(() => {
    window.removeEventListener("keydown", onKeydown)
  })
  return (
    <ImageWithError
      maxH="75vh"
      rounded="$lg"
      src={objStore.raw_url}
      fallback={<FullLoading />}
      fallbackErr={<Error msg={t("home.preview.failed_load_img")} />}
    />
  )
}

export default Preview

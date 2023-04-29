

def predict_step(image_paths):
  from transformers import VisionEncoderDecoderModel, ViTFeatureExtractor, AutoTokenizer
  import torch
  from PIL import Image
  from io import BytesIO
  import requests 

  model_path = "../model/"
  model = VisionEncoderDecoderModel.from_pretrained(model_path)
  feature_extractor = ViTFeatureExtractor.from_pretrained(model_path)
  tokenizer = AutoTokenizer.from_pretrained(model_path)

  device = torch.device("cpu" if torch.cuda.is_available() else "cpu")
  model.to(device)
  max_length = 16
  num_beams = 4
  gen_kwargs = {"max_length": max_length, "num_beams": num_beams}
  images = []
  for image_path in image_paths:
    response = requests.get(image_path)
    i_image = Image.open(BytesIO(response.content))
    if i_image.mode != "RGB":
      i_image = i_image.convert(mode="RGB")

    images.append(i_image)

  pixel_values = feature_extractor(images=images, return_tensors="pt").pixel_values
  pixel_values = pixel_values.to(device)

  output_ids = model.generate(pixel_values, **gen_kwargs)

  preds = tokenizer.batch_decode(output_ids, skip_special_tokens=True)
  preds = [pred.strip() for pred in preds]
  return preds


print(predict_step(["https://admmedia.s3.ap-south-1.amazonaws.com/user_uploads/img_0390164a-4946-469e-ae1a-b4cbff3e8dbb"])) # ['a woman in a hospital bed with a woman in a hospital bed']

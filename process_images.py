from Tkinter import *
from tkFileDialog import askdirectory
from tkinter import messagebox

import os, PIL
import numpy as np
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import math

def _compose_alpha(img_in, img_layer, opacity):

    comp_alpha = np.minimum(img_in[:, :, 3], img_layer[:, :, 3])*opacity

    new_alpha = img_in[:, :, 3] + (1.0 - img_in[:, :, 3])*comp_alpha
    np.seterr(divide='ignore', invalid='ignore')
    ratio = comp_alpha/new_alpha
    ratio[ratio == np.NAN] = 0.0
    return ratio

def multiply(img_in, img_layer, opacity):

    img_in /= 255.0
    img_layer /= 255.0

    ratio = _compose_alpha(img_in, img_layer, opacity)

    comp = np.clip(img_layer[:, :, :3] * img_in[:, :, :3], 0.0, 1.0)

    ratio_rs = np.reshape(np.repeat(ratio, 3), [comp.shape[0], comp.shape[1], comp.shape[2]])
    img_out = comp * ratio_rs + img_in[:, :, :3] * (1.0 - ratio_rs)
    img_out = np.nan_to_num(np.dstack((img_out, img_in[:, :, 3])))  # add alpha channel and replace nans
    return img_out*255.0

def darken_only(img_in, img_layer, opacity):

    img_in /= 255.0
    img_layer /= 255.0

    ratio = _compose_alpha(img_in, img_layer, opacity)

    comp = np.minimum(img_in[:, :, :3], img_layer[:, :, :3])

    ratio_rs = np.reshape(np.repeat(ratio, 3), [comp.shape[0], comp.shape[1], comp.shape[2]])
    img_out = comp*ratio_rs + img_in[:, :, :3] * (1.0-ratio_rs)
    img_out = np.nan_to_num(np.dstack((img_out, img_in[:, :, 3])))  # add alpha channel and replace nans
    return img_out*255.0


def run(dir_path, gen_size, gen_stride = 1, des_stride = 1, mode = 2, make_index = True, mix = .8, aspect = 2.0):

	print dir_path

	files = os.listdir(dir_path)
	imlist = [filename for filename in files if filename[-4:] in [".png",".PNG", ".jpg", ".JPG"]]

	des_nums = []

	for im in imlist:
		try:
			des_nums.append(int(im.split('.')[0]))
		except ValueError:
			des_nums.append(None)
			print "could not process image with name:", im

	print "found", len(des_nums), "images"

	chunks = [range(x, x+gen_size, des_stride) for x in range(0, max(des_nums), gen_size)]
	chunks = [c for i,c in enumerate(chunks) if i % gen_stride == 0]

	im_sets = []

	for chunk in chunks:
		im_sets.append([])
		for c in chunk:
			try:
				indx = des_nums.index(c)
			except ValueError:
				# print "could not find image", c
				continue
			im_sets[-1].append(imlist[indx])

	target_dir = dir_path + "/composites"

	if not os.path.exists(target_dir):
	    os.makedirs(target_dir)

	final_images = []

	for i, im_set in enumerate(im_sets):

		img_id = i * gen_stride

		w,h = Image.open(dir_path + "/" + im_set[0]).size
		num_images = len(im_set)

		txt_height = int(min([w,h]) * 0.05)

		img_out = np.zeros((h,w,4),np.float)
		comp = np.ones((h,w,4),np.float) * 255.0
			
		for im in im_set:
			imarr = np.ones((h,w,4),np.float) * 255.0
			imarr[:,:,:3] = np.array(Image.open(dir_path + "/" + im), dtype=np.float)

			if mode == "multiply":
				comp = multiply(imarr, comp, mix)
				img_out = img_out + comp / num_images
			elif mode == "darken":
				comp = darken_only(imarr, comp, mix)
				img_out = img_out + comp / num_images
			else:
				img_out = img_out + imarr / num_images

		arr = np.ones((h+int(txt_height*1.5),w,3),np.float) * 255.0
		arr[:h,:,:] = img_out[:,:,:3]

		arr = np.array(np.round(arr), dtype=np.uint8)
		out = Image.fromarray(arr, mode="RGB")

		draw = ImageDraw.Draw(out)
		font = ImageFont.truetype("arial.ttf", txt_height)
		draw.text((int(w*0.1), h),str(img_id),font=font,fill=(0,0,0))

		target = target_dir + "/" + str(img_id).zfill(4) + ".png"
		out.save(target)

		final_images.append(out)

		print "saved image to:", target

	if make_index:

		w,h = final_images[0].size

		print w, h

		x_dim = int(math.ceil( aspect * h * len(final_images) / w ) ** 0.5)
		y_dim = int(math.ceil(len(final_images) / float(x_dim)))

		print "making index with dimensions:", x_dim, "x", y_dim

		img_out = np.ones((h*y_dim,w*x_dim,3),np.float) * 255.0

		count = 0

		for y in range(y_dim):
			for x in range(x_dim):
				try:
					imarr = np.array(final_images[count], dtype=np.float)
					img_out[y*h:(y+1)*h,x*w:(x+1)*w,:] = imarr
				except IndexError:
					break
				count += 1

		arr = np.array(np.round(img_out), dtype=np.uint8)
		out = Image.fromarray(arr, mode="RGB")

		target = target_dir + "/index.png"
		out.save(target)

		print "saved image to:", target

class App:

	def __init__(self, master):

		pad = 3

		frame = Frame(master, padx=10, pady=10)
		frame.pack()

		button_dir = Button(frame, text="Set directory", command=self.get_directory)
		button_dir.grid(row=0, column=0, padx=pad, pady=pad*2, sticky=E)

		self.dir = StringVar()
		self.dir.set("No directory set!")
		Label(frame, textvariable=self.dir).grid(row=0, column=1, padx=pad, pady=pad, sticky=W)

		Label(frame, text="Overlay mode:").grid(row=1, column=0, padx=pad, pady=pad, sticky=E)
		self.mode = StringVar()
		self.mode.set("transparency")
		OptionMenu(frame, self.mode, "transparency", "multiply", "darken").grid(row=1, column=1, padx=pad, pady=pad, sticky=W)

		Label(frame, text="Blend factor:").grid(row=2, column=0, padx=pad, pady=pad, sticky=E)
		self.mix = DoubleVar()
		self.mix.set(0.8)
		Entry(frame, textvariable=self.mix).grid(row=2, column=1, padx=pad, pady=pad, sticky=W)

		Label(frame, text="Designs per generation:").grid(row=3, column=0, padx=pad, pady=pad, sticky=E)
		self.gen_size = IntVar()
		self.gen_size.set(100)
		Entry(frame, textvariable=self.gen_size).grid(row=3, column=1, padx=pad, pady=pad, sticky=W)

		Label(frame, text="Use nth generation:").grid(row=4, column=0, padx=pad, pady=pad, sticky=E)
		self.gen_stride = IntVar()
		self.gen_stride.set(1)
		Entry(frame, textvariable=self.gen_stride).grid(row=4, column=1, padx=pad, pady=pad, sticky=W)

		Label(frame, text="Use nth design:").grid(row=5, column=0, padx=pad, pady=pad, sticky=E)
		self.des_stride = IntVar()
		self.des_stride.set(1)
		Entry(frame, textvariable=self.des_stride).grid(row=5, column=1, padx=pad, pady=pad, sticky=W)

		Label(frame, text="Make index").grid(row=6, column=0, padx=pad, pady=pad, sticky=E)
		self.make_index = BooleanVar()
		self.make_index.set(True)
		Checkbutton(frame, variable=self.make_index).grid(row=6, column=1, padx=pad, pady=pad, sticky=W)

		Label(frame, text="Aspect:").grid(row=7, column=0, padx=pad, pady=pad, sticky=E)
		self.aspect = DoubleVar()
		self.aspect.set(2.0)
		Entry(frame, textvariable=self.aspect).grid(row=7, column=1, padx=pad, pady=pad, sticky=W)

		self.button_run = Button(frame, text="Run", command=self.run_app)
		self.button_run.grid(row=8, columnspan=2, padx=pad*2, pady=10)



	def get_directory(self):
		self.dir.set(askdirectory(title="Select directory with image files:", mustexist=1))
		# self.dir_label.set(self.dir)
		print self.dir

	def run_app(self):

		dir_path = self.dir.get()

		try:
			os.listdir(dir_path)
		except WindowsError:
			return messagebox.showerror("Error", "Please select valid directory!")

		mix = self.mix.get()
		mode = self.mode.get()
		gen_size = self.gen_size.get()
		gen_stride = self.gen_stride.get()
		des_stride = self.des_stride.get()
		make_index = self.make_index.get()
		aspect = self.aspect.get()

		print dir_path, mix, mode, gen_size, gen_stride, des_stride, make_index, aspect

		run(dir_path, gen_size, gen_stride, des_stride, mode, make_index, mix, aspect)



if __name__ == "__main__":

	root = Tk()
	root.title("Process images")
	# root.iconbitmap(default='icon.ico')
	app = App(root)
	root.mainloop()
	root.destroy()





